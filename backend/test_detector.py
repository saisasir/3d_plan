"""Diagnostic test of room extraction — step by step."""
import sys
sys.path.insert(0, ".")
import cv2
import numpy as np

img = cv2.imread("real_floorplan.jpg")
print(f"Image shape: {img.shape}")

# Step 1: Crop title block
from app.cv.wall_detector import OpenCVWallDetector
detector = OpenCVWallDetector()
drawing = detector._crop_drawing_area(img)
dh, dw = drawing.shape[:2]
print(f"Cropped: {drawing.shape}")

# Step 2: Wall mask
wall_mask = detector._extract_wall_mask(drawing)
wall_px = cv2.countNonZero(wall_mask)
print(f"Wall mask: {wall_px} white pixels ({wall_px*100/(dh*dw):.1f}%)")
cv2.imwrite("debug_1_wall_mask.png", wall_mask)

# Step 3: Thicken + close (same as _extract_rooms)
k_thick = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
thick = cv2.dilate(wall_mask, k_thick, iterations=2)
k_close = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
thick = cv2.morphologyEx(thick, cv2.MORPH_CLOSE, k_close, iterations=2)
k_solid = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
thick_walls = cv2.dilate(thick, k_solid, iterations=1)

# Draw bounding box to seal the house
bx, by, bw, bh = cv2.boundingRect(thick_walls)
cv2.rectangle(thick_walls, (bx, by), (bx + bw, by + bh), 255, 10)

thick_px = cv2.countNonZero(thick_walls)
print(f"Thick walls: {thick_px} white pixels ({thick_px*100/(dh*dw):.1f}%)")
cv2.imwrite("debug_2_thick_walls.png", thick_walls)

# Step 4: Invert
interior = cv2.bitwise_not(thick_walls)
cv2.imwrite("debug_3_interior.png", interior)
int_px = cv2.countNonZero(interior)
print(f"Interior: {int_px} white pixels ({int_px*100/(dh*dw):.1f}%)")

# Step 5: CC before flood-fill
num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(interior, connectivity=4)
print(f"\nComponents BEFORE flood-fill: {num_labels - 1}")
for i in range(1, min(num_labels, 20)):
    area = stats[i, cv2.CC_STAT_AREA]
    pct = area * 100 / (dh * dw)
    cx, cy = centroids[i]
    print(f"  #{i}: area={area} ({pct:.1f}%) center=({cx:.0f},{cy:.0f})")

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

cv2.imwrite("debug_4_after_fill.png", interior)
int_px_after = cv2.countNonZero(interior)
print(f"\nAfter flood-fill: {int_px_after} white pixels ({int_px_after*100/(dh*dw):.1f}%)")

num_labels2, labels2, stats2, centroids2 = cv2.connectedComponentsWithStats(interior, connectivity=4)
print(f"Components AFTER flood-fill: {num_labels2 - 1}")
for i in range(1, min(num_labels2, 20)):
    area = stats2[i, cv2.CC_STAT_AREA]
    pct = area * 100 / (dh * dw)
    print(f"  #{i}: area={area} ({pct:.2f}%)")
