import os
from ultralytics import YOLO
import numpy as np
import cv2

class FloorPlanDetector:
    def __init__(self, model_path: str = "ai_models/best.pt"):
        self.model_path = model_path
        self.model = None
        
        # Load model if weights exist, otherwise initialize as None
        if os.path.exists(self.model_path):
            self.model = YOLO(self.model_path)
        else:
            print(f"Warning: Model weights not found at {self.model_path}. Please download them.")

    def detect_symbols(self, image: np.ndarray, confidence: float = 0.25):
        """
        Detect doors, windows, and furniture symbols in a floor plan image.
        Returns a list of detections with coordinates and class names.
        """
        if self.model is None:
            return []

        results = self.model.predict(image, conf=confidence)
        detections = []

        for r in results:
            boxes = r.boxes
            for box in boxes:
                # Get coordinates
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                
                # Get class index and confidence
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                class_name = self.model.names[cls_id]

                detections.append({
                    "class": class_name,
                    "confidence": conf,
                    "bbox": [x1, y1, x2, y2],
                    "center": [(x1 + x2) / 2, (y1 + y2) / 2]
                })

        return detections

    def detect_segments(self, image: np.ndarray):
        """
        Detect room polygons and walls using Instance Segmentation.
        """
        if self.model is None:
            return []

        # Assuming the model is trained for segmentation (yolov8-seg)
        results = self.model.predict(image, task="segment")
        segments = []

        for r in results:
            if r.masks is not None:
                for i, mask in enumerate(r.masks.xy):
                    cls_id = int(r.boxes.cls[i])
                    class_name = self.model.names[cls_id]
                    
                    segments.append({
                        "class": class_name,
                        "polygon": mask.tolist()
                    })

        return segments
