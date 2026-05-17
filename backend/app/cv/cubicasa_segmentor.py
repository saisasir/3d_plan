import torch
import cv2
import numpy as np
from app.cv.cubicasa_model import CubiCasaModel
import os

class CubiCasaSegmentor:
    def __init__(self, weights_path: str = "ai_models/cubicasa_weights.pkl"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = CubiCasaModel().to(self.device)
        
        if os.path.exists(weights_path):
            print(f"Loading CubiCasa weights from {weights_path}...")
            # Load with map_location to handle CPU/GPU differences
            checkpoint = torch.load(weights_path, map_location=self.device)
            
            # The weights might be in a 'state_dict' or direct
            state_dict = checkpoint.get('state_dict', checkpoint)
            
            # Remove 'module.' prefix if trained with DataParallel
            new_state_dict = {k.replace('module.', ''): v for k, v in state_dict.items()}
            
            self.model.load_state_dict(new_state_dict, strict=False)
            self.model.eval()
            self.enabled = True
        else:
            print(f"Warning: Weights not found at {weights_path}")
            self.enabled = False

    @torch.no_grad()
    def predict(self, image: np.ndarray):
        """Perform high-sensitivity inference."""
        if not self.enabled:
            return {
                "room_mask": np.zeros(image.shape[:2], dtype=np.uint8),
                "opening_heatmap": np.zeros((1, 512, 512), dtype=np.float32),
                "raw_room_probs": None
            }

        print(f"--- STARTING NEURAL INFERENCE FOR: {image.shape} ---")
        # 1. Preprocess
        original_h, original_w = image.shape[:2]
        img = cv2.resize(image, (512, 512))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) # CRITICAL: Swap to RGB for AI
        img = img.astype(np.float32) / 255.0
        # Neural Normalization (ImageNet Standards for Hourglass Backbone)
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        img = (img - mean) / std
        img = torch.from_numpy(img).permute(2, 0, 1).unsqueeze(0).to(self.device)

        # 2. Forward Pass
        # Returns list of stacks [[rooms, openings, walls], [rooms, openings, walls]]
        outputs = self.model(img)
        
        # Take predictions from the last stack
        room_pred, opening_pred, wall_pred = outputs[-1]
        
        # 3. Post-process
        # Room Segmentation (softmax)
        room_mask = torch.softmax(room_pred, dim=1).cpu().numpy()[0]
        room_class = np.argmax(room_mask, axis=0)
        
        # Opening/Heatmap Detection
        opening_mask = torch.sigmoid(opening_pred).cpu().numpy()[0]
        
        # Resize back to original
        full_room_mask = cv2.resize(room_class.astype(np.uint8), (original_w, original_h), interpolation=cv2.INTER_NEAREST)
        
        # NEURAL DIAGNOSTIC: See what the AI actually found
        unique_classes = np.unique(full_room_mask)
        print(f"--- AI NEURAL SCAN: Detected Class IDs {unique_classes.tolist()} ---")
        
        return {
            "room_mask": full_room_mask,
            "opening_heatmap": opening_mask,
            "raw_room_probs": room_mask
        }

    def get_polygons_from_mask(self, mask: np.ndarray, class_idx: int):
        """
        Convert a specific room class mask into polygons.
        """
        binary = (mask == class_idx).astype(np.uint8) * 255
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        polygons = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 1000: # Ignore tiny softmax artifacts
                poly = cnt.reshape(-1, 2).tolist()
                polygons.append(poly)
        
        if polygons:
            print(f"--- CLASS {class_idx}: Found {len(polygons)} polygons ---")
        return polygons
