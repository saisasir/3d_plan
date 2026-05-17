import cv2
import os
import numpy as np
from PIL import Image
import io
from pdf2image import convert_from_bytes

class FloorPlanPreprocessor:
    @staticmethod
    def process_pdf(pdf_bytes: bytes):
        """Convert first page of PDF to image."""
        # Check for bundled poppler
        poppler_path = os.path.join(os.getcwd(), "poppler", "poppler-24.08.0", "Library", "bin")
        if not os.path.exists(poppler_path):
            poppler_path = None # Fallback to system PATH

        try:
            images = convert_from_bytes(pdf_bytes, poppler_path=poppler_path)
            if not images:
                return None
            # Convert PIL to OpenCV format
            open_cv_image = np.array(images[0])
            return cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"[Preprocessor] PDF Conversion error: {e}")
            raise e

    @staticmethod
    def deskew(image: np.ndarray):
        """Find dominant angle and rotate image to straighten walls."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)
        
        if lines is None:
            return image

        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            # Focus on near-horizontal or near-vertical lines
            if abs(angle) < 45:
                angles.append(angle)
            elif abs(angle) > 45:
                angles.append(angle - 90 if angle > 0 else angle + 90)

        if not angles:
            return image

        median_angle = np.median(angles)
        
        # Rotate image
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        return rotated

    @staticmethod
    def clean_and_binarize(image: np.ndarray):
        """Prepare image for AI detection."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Adaptive thresholding to handle lighting variations
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Denoising
        kernel = np.ones((3,3), np.uint8)
        denoised = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        return denoised
