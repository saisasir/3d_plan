"""Diagnostic test of wall extraction strategies."""
import sys
sys.path.insert(0, ".")
import cv2
import numpy as np
from app.cv.wall_detector import OpenCVWallDetector

img = cv2.imread("real_floorplan.jpg")
detector = OpenCVWallDetector()
drawing = detector._crop_drawing_area(img)
dh, dw = drawing.shape[:2]

wall_mask = detector._extract_wall_mask(drawing)
k_thick = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
thick = cv2.dilate(wall_mask, k_thick, iterations=2)
k_close = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
thick = cv2.morphologyEx(thick, cv2.MORPH_CLOSE, k_close, iterations=2)
k_solid = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
thick = cv2.dilate(thick, k_solid, iterations=1)

# Draw bounding box to seal the house
bx, by, bw, bh = cv2.boundingRect(thick)
cv2.rectangle(thick, (bx, by), (bx + bw, by + bh), 255, 10)

interior = cv2.bitwise_not(thick)

# Step 6: Flood-fill from edges
exterior_mask = np.zeros((dh + 2, dw + 2), np.uint8)
for seed in [(0, 0), (dw - 1, 0), (0, dh - 1), (dw - 1, dh - 1)]:
    if interior[seed[1], seed[0]] == 255:
        cv2.floodFill(interior, exterior_mask, seed, 0)

step = max(10, min(dh, dw) // 20)
for x in range(0, dw, step):
    if interior[0, x] == 255:
        cv2.floodFill(interior, exterior_mask, (x, 0), 0)
    if interior[dh - 1, x] == 255:
        cv2.floodFill(interior, exterior_mask, (x, dh - 1), 0)
for y in range(0, dh, step):
    if interior[y, 0] == 255:
        cv2.floodFill(interior, exterior_mask, (0, y), 0)
    if interior[y, dw - 1] == 255:
        cv2.floodFill(interior, exterior_mask, (dw - 1, y), 0)

# The exterior_mask shows exactly where the floodfill went.
# exterior_mask is (dh+2, dw+2) and values are 1 where filled
cv2.imwrite("debug_exterior_fill.png", exterior_mask * 255)
cv2.imwrite("debug_thick_walls_for_leak.png", thick)
print("Saved debug_exterior_fill.png")
