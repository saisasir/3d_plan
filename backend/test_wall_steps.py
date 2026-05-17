"""Diagnostic test of wall extraction strategies."""
import sys
sys.path.insert(0, ".")
import cv2
import numpy as np
from app.cv.wall_detector import OpenCVWallDetector

img = cv2.imread("real_floorplan.jpg")
print(f"Image shape: {img.shape}")

detector = OpenCVWallDetector()
drawing = detector._crop_drawing_area(img)
cv2.imwrite("debug_crop.png", drawing)

gray = cv2.cvtColor(drawing, cv2.COLOR_BGR2GRAY)
cv2.imwrite("debug_gray.png", gray)

_, binary = cv2.threshold(gray, 210, 255, cv2.THRESH_BINARY_INV)
cv2.imwrite("debug_binary.png", binary)

hsv = cv2.cvtColor(drawing, cv2.COLOR_BGR2HSV)
dark_mask = cv2.inRange(hsv, (0, 0, 0), (180, 120, 220))
cv2.imwrite("debug_dark_mask.png", dark_mask)

binary_a = cv2.bitwise_and(binary, dark_mask)
cv2.imwrite("debug_binary_a.png", binary_a)

h, w = drawing.shape[:2]
min_len = max(8, min(h, w) // 80)
h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (min_len, 1))
v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, min_len))

h_walls = cv2.morphologyEx(binary_a, cv2.MORPH_OPEN, h_kernel)
v_walls = cv2.morphologyEx(binary_a, cv2.MORPH_OPEN, v_kernel)
strat_a = cv2.bitwise_or(h_walls, v_walls)
cv2.imwrite("debug_strat_a.png", strat_a)

_, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
otsu = cv2.bitwise_and(otsu, dark_mask)
cv2.imwrite("debug_otsu.png", otsu)

k_erode = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
eroded = cv2.erode(otsu, k_erode, iterations=1)
cv2.imwrite("debug_eroded.png", eroded)

k_dilate_b = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
strat_b = cv2.dilate(eroded, k_dilate_b, iterations=1)
cv2.imwrite("debug_strat_b.png", strat_b)

walls = cv2.bitwise_or(strat_a, strat_b)
cv2.imwrite("debug_walls_combined.png", walls)

print("Saved intermediate steps.")
