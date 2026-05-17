import torch
import cv2
import numpy as np
from realesrgan import RealESRGANer
from basicsr.archs.rrdbnet_arch import RRDBNet
import os

class UpscaleService:
    def __init__(self):
        # Initialize the model architecture
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
        
        # Path to pre-trained weights (in backend/ai_models/)
        model_path = os.path.join("ai_models", "RealESRGAN_x4plus.pth")
        
        # If weights aren't there, we skip upscaling to prevent crash during dev
        self.enabled = os.path.exists(model_path)
        
        if self.enabled:
            self.upsampler = RealESRGANer(
                scale=4,
                model_path=model_path,
                model=model,
                tile=400,
                tile_pad=10,
                pre_pad=0,
                half=True if torch.cuda.is_available() else False # Use half precision if GPU
            )
        else:
            print("[WARNING] Real-ESRGAN weights not found. Upscaling will be skipped.")

    def enhance(self, image: np.ndarray) -> np.ndarray:
        """
        Upscales the image by 4x and removes noise/artifacts.
        """
        if not self.enabled:
            return image
            
        output, _ = self.upsampler.enhance(image, outscale=4)
        return output
