"""
OpenCV-based wall and room detector — v3.
Robust floor plan parser for professional architectural plans.

Strategy for complex plans (with furniture, title blocks, colors):
1. Convert to grayscale and detect the drawing boundary (crop title block)
2. Use multiple thresholding strategies
3. Focus on THICK dark lines as walls (furniture/text lines are thin)
4. Use morphological filtering tuned for wall thickness
5. Extract rooms via flood-fill of enclosed spaces
6. Derive clean walls from room polygon edges
"""
import cv2
import numpy as np
from typing import List, Dict, Tuple
import math


class OpenCVWallDetector:
    """
    Self-contained floor plan parser using classical CV.
    Handles complex architectural plans with furniture, text, and title blocks.
    """

    def __init__(self):
        self.min_room_area_ratio = 0.006   # min room = 0.6% of drawing area (filters furniture)
        self.max_room_area_ratio = 0.80    # max room = 80% of drawing area

    # ------------------------------------------------------------------ #
    #  PUBLIC ENTRY POINT
    # ------------------------------------------------------------------ #
    def analyze(self, image: np.ndarray) -> Dict:
        h, w = image.shape[:2]

        # 1. Crop the title block and outer border
        drawing = self._crop_drawing_area(image)
        dh, dw = drawing.shape[:2]
        total_area = dh * dw

        # 2. Extract masks using BOTH strategies
        mask_standard = self._extract_wall_mask(drawing)
        mask_hough = self._extract_wall_mask_alternative(drawing)

        # 3. Detect rooms for both
        rooms_standard = self._extract_rooms(mask_standard, drawing, dh, dw, total_area)
        rooms_hough = self._extract_rooms(mask_hough, drawing, dh, dw, total_area)

        # 4. Pick the strategy that found the most valid architectural area
        area_standard = sum(r["area_px"] for r in rooms_standard)
        area_hough = sum(r["area_px"] for r in rooms_hough)

        if area_hough > area_standard:
            rooms = rooms_hough
            wall_mask = mask_hough
            print(f"[OpenCVWallDetector] Selected Hough strategy (Area: {area_hough:.0f} px)")
        else:
            rooms = rooms_standard
            wall_mask = mask_standard
            print(f"[OpenCVWallDetector] Selected Standard strategy (Area: {area_standard:.0f} px)")

        # 5. Detect openings
        openings = self._detect_openings(wall_mask, drawing, dh, dw)

        # 6. Derive walls from room boundaries
        walls = self._derive_walls_from_rooms(rooms)

        # 7. Estimate scale
        scale = self._estimate_scale(openings, rooms, dh, dw)

        # Adjust coordinates if we cropped
        offset_x, offset_y = self._crop_offset
        for room in rooms:
            room["polygon"] = [[p[0] + offset_x, p[1] + offset_y] for p in room["polygon"]]
            room["center"] = [room["center"][0] + offset_x, room["center"][1] + offset_y]
        for wall in walls:
            wall["points"] = [[p[0] + offset_x, p[1] + offset_y] for p in wall["points"]]
        for op in openings:
            op["position"] = [op["position"][0] + offset_x, op["position"][1] + offset_y]

        return {
            "rooms": rooms,
            "walls": walls,
            "openings": openings,
            "scale_factor": scale,
            "image_dims": {"w": w, "h": h},
        }

    # ------------------------------------------------------------------ #
    #  CROP DRAWING AREA (remove title block, borders)
    # ------------------------------------------------------------------ #
    _crop_offset = (0, 0)

    def _crop_drawing_area(self, image: np.ndarray) -> np.ndarray:
        """Remove title block (usually bottom 10-15%) and outer border."""
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Detect if there's a title block at the bottom
        # Title blocks have high density of text/lines in the bottom region
        bottom_strip = gray[int(h * 0.82):, :]
        _, bottom_bin = cv2.threshold(bottom_strip, 200, 255, cv2.THRESH_BINARY_INV)
        bottom_density = cv2.countNonZero(bottom_bin) / bottom_strip.size

        # If bottom strip has high density (>8%), it's likely a title block
        crop_bottom = h
        if bottom_density > 0.08:
            # Find the horizontal line separating the title block
            # Look for a strong horizontal edge in the bottom 25%
            edges = cv2.Canny(gray[int(h * 0.70):, :], 50, 150)
            h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (w // 3, 1))
            h_lines = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, h_kernel)
            rows = np.where(np.sum(h_lines, axis=1) > w * 0.3 * 255)[0]
            if len(rows) > 0:
                crop_bottom = int(h * 0.70) + rows[0] - 5
            else:
                crop_bottom = int(h * 0.82)

        # Also detect outer border and crop inward
        # Look for strong lines near edges
        margin = 3 # Minimal crop to preserve drawn bounding boxes
        crop_top = margin
        crop_left = margin
        crop_right = w - margin

        self._crop_offset = (crop_left, crop_top)
        cropped = image[crop_top:crop_bottom, crop_left:crop_right]

        if cropped.size == 0:
            self._crop_offset = (0, 0)
            return image

        return cropped

    # ------------------------------------------------------------------ #
    #  WALL MASK EXTRACTION — Primary Strategy
    # ------------------------------------------------------------------ #
    def _extract_wall_mask(self, image: np.ndarray) -> np.ndarray:
        """
        Extract walls while ensuring connectivity.
        """
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Remove small dark noise (like dot grids) by closing the white background
        k_clean_dots = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, k_clean_dots)

        # 1. Balanced adaptive threshold
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 21, 10
        )

        # 2. Gentle cleaning (don't kill the corners)
        kernel_clean = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        walls = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_clean)
        
        # 3. LENGTH FILTER (Very gentle)
        # Only remove very tiny specks of noise
        line_min_len = 10 
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(walls, connectivity=8)
        mask = np.zeros_like(walls)
        for i in range(1, num_labels):
            if stats[i, cv2.CC_STAT_WIDTH] > line_min_len or stats[i, cv2.CC_STAT_HEIGHT] > line_min_len:
                mask[labels == i] = 255
        
        return mask

    def _extract_wall_mask_alternative(self, image: np.ndarray) -> np.ndarray:
        """
        Hough-line based strategy.
        Specifically designed to handle 3D renders and noisy colored floor plans
        by extracting only long, straight architectural lines and ignoring furniture/textures.
        """
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 1. Edge detection with blurring to kill carpet/wood textures
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 40, 120)
        
        # 2. Extract long straight lines (walls)
        min_line_length = max(20, int(max(h, w) * 0.03)) # 3% of image
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, 
            threshold=40, 
            minLineLength=min_line_length, 
            maxLineGap=15
        )
        
        # 3. Draw the lines on a blank mask
        mask = np.zeros((h, w), dtype=np.uint8)
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                # Draw thick lines to ensure they connect
                cv2.line(mask, (x1, y1), (x2, y2), 255, 6)
                
        # 4. Connect corners and clean up
        k_close = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k_close)
        
        return mask

    def _extract_rooms(self, wall_mask: np.ndarray, orig_image: np.ndarray,
                       h: int, w: int, total_area: int) -> List[Dict]:
        """
        Extract rooms by flood-filling enclosed spaces.
        Uses a robust leak-proof thickened wall mask to prevent flood-fill leakage
        while relying on downstream 2D pairwise snapping to seamlessly close all gaps.
        """
        # 1. Create a bulletproof wall mask
        # Safe kernel size to preserve small rooms
        close_size = max(15, min(int(max(h, w) * 0.03) | 1, 35))
        k_close = cv2.getStructuringElement(cv2.MORPH_RECT, (close_size, close_size))
        k_thick = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        solid_walls = cv2.morphologyEx(wall_mask, cv2.MORPH_CLOSE, k_close)
        solid_walls = cv2.dilate(solid_walls, k_thick, iterations=1)
        
        # CLEAR THE BORDERS! This breaks any outer "paper bounding box" 
        # so the flood-fill can successfully flood the yard.
        border = max(10, int(min(h, w) * 0.015))
        solid_walls[0:border, :] = 0
        solid_walls[-border:, :] = 0
        solid_walls[:, 0:border] = 0
        solid_walls[:, -border:] = 0
        
        # 2. Invert to get spaces
        space = cv2.bitwise_not(solid_walls)
        
        # 3. Identify exterior (flood-fill from border)
        space_filled = space.copy()
        step = max(10, min(h, w) // 100)
        for x in [0, w-1]:
            for y in range(0, h, step):
                cv2.floodFill(space_filled, None, (x, y), 0)
        for y in [0, h-1]:
            for x in range(0, w, step):
                cv2.floodFill(space_filled, None, (x, y), 0)

        # 4. EXPAND rooms aggressively to close the wall gap and overlap interfaces
        expand_size = int(max(h, w) * 0.02) | 1
        k_expand = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (expand_size, expand_size))
        space_filled = cv2.dilate(space_filled, k_expand, iterations=1)

        # 5. Connected components for rooms
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(space_filled, connectivity=4)
        
        rooms = []
        min_area = total_area * (self.min_room_area_ratio * 0.3) # More lenient
        max_area = total_area * self.max_room_area_ratio

        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area < min_area or area > max_area:
                continue
                
            mask = (labels == i).astype(np.uint8) * 255
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue
                
            cnt = max(contours, key=cv2.contourArea)
            
            # Filter title blocks (long horizontal strips near the bottom)
            rx, ry, rw, rh = cv2.boundingRect(cnt)
            if rh > 0 and (rw / rh > 8.0) and (ry > h * 0.85):
                continue
                
            # Higher epsilon for cleaner, straighter edges
            epsilon = 0.005 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            
            if len(approx) < 3:
                continue
                
            # ORTHOGONALIZE: Snap edges to 0/90 degrees
            poly = approx.reshape(-1, 2)
            ortho_poly = self._orthogonalize_polygon(poly)
            
            rooms.append({
                "id": f"room_{i}",
                "name": "Unnamed Room",
                "area_px": float(area),
                "center": [float(centroids[i][0]), float(centroids[i][1])],
                "polygon": ortho_poly.tolist(),
                "type": "room"
            })
            
        rooms.sort(key=lambda r: r["area_px"], reverse=True)
        return self._classify_rooms(rooms, h, w)

    def _orthogonalize_polygon(self, poly):
        """
        Robustly force a polygon to have only 0 or 90 degree angles.
        Prevents jagged edges and slanted walls.
        """
        if len(poly) < 3: return poly
        
        ortho = []
        n = len(poly)
        for i in range(n):
            p1 = poly[i]
            p2 = poly[(i + 1) % n]
            
            dx = abs(p2[0] - p1[0])
            dy = abs(p2[1] - p1[1])
            
            # Snap to axis
            if dx > dy:
                p2[1] = p1[1]
            else:
                p2[0] = p1[0]
            
            ortho.append(p1.tolist())
            
        # Deduplicate and return
        res = []
        for p in ortho:
            if not res or (p[0] != res[-1][0] or p[1] != res[-1][1]):
                res.append(p)
        return np.array(res)

    def _classify_rooms(self, rooms: List[Dict], h: int, w: int) -> List[Dict]:
        type_sequence = ["living_room", "bedroom", "bedroom", "kitchen", "bathroom", "hallway", "room"]
        for i, room in enumerate(rooms):
            rtype = type_sequence[min(i, len(type_sequence)-1)]
            room["type"] = rtype
            room["name"] = rtype.replace("_", " ").title()
        return rooms

    def _derive_walls_from_rooms(self, rooms: List[Dict]) -> List[Dict]:
        """
        Derive walls from room polygons and SNAP them to avoid floating detached walls.
        """
        all_edges = []
        for room in rooms:
            poly = room["polygon"]
            for i in range(len(poly)):
                p1, p2 = poly[i], poly[(i+1)%len(poly)]
                all_edges.append((tuple(p1), tuple(p2)))
        
        if not all_edges: return []

        unique_walls = []
        seen_edges = []
        snap_dist = 40.0 # Aggressive snap for high-res plans
        min_wall_len = 15.0 # Ignore tiny fragments

        for p1, p2 in all_edges:
            length = math.hypot(p1[0]-p2[0], p1[1]-p2[1])
            if length < min_wall_len:
                continue

            # Normalize edge
            edge_sorted = sorted([p1, p2])
            
            # Check if close to any seen edge
            found = False
            for existing in seen_edges:
                d1 = math.hypot(edge_sorted[0][0] - existing[0][0], edge_sorted[0][1] - existing[0][1])
                d2 = math.hypot(edge_sorted[1][0] - existing[1][0], edge_sorted[1][1] - existing[1][1])
                
                if d1 < snap_dist and d2 < snap_dist:
                    found = True
                    break
            
            if not found:
                seen_edges.append(edge_sorted)
                unique_walls.append({
                    "points": [list(p1), list(p2)],
                    "length_px": float(length)
                })
        
        return unique_walls

    # ------------------------------------------------------------------ #
    #  OPENING DETECTION
    # ------------------------------------------------------------------ #
    def _detect_openings(self, wall_mask: np.ndarray, image: np.ndarray,
                         h: int, w: int) -> List[Dict]:
        openings = []

        # Detect door arcs using circle detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        circles = cv2.HoughCircles(
            cv2.GaussianBlur(edges, (5, 5), 0),
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=50,
            param1=80,
            param2=30,
            minRadius=20,
            maxRadius=min(h, w) // 8
        )

        if circles is not None:
            for c in circles[0][:15]:  # cap at 15
                cx, cy, r = c
                # Verify near a wall
                check_y = int(np.clip(cy, 0, h - 1))
                check_x = int(np.clip(cx, 0, w - 1))
                y_lo = max(0, check_y - int(r))
                y_hi = min(h, check_y + int(r))
                x_lo = max(0, check_x - int(r))
                x_hi = min(w, check_x + int(r))
                wall_region = wall_mask[y_lo:y_hi, x_lo:x_hi]
                if wall_region.size == 0:
                    continue
                wall_density = cv2.countNonZero(wall_region) / (wall_region.size + 1)

                if 0.05 < wall_density < 0.6:
                    too_close = any(
                        math.hypot(cx - e["position"][0], cy - e["position"][1]) < 40
                        for e in openings
                    )
                    if not too_close:
                        openings.append({
                            "type": "door",
                            "position": [float(cx), float(cy)],
                            "width": float(r * 2),
                            "rotation": 0.0,
                        })

        return openings[:20]

    # ------------------------------------------------------------------ #
    #  SCALE ESTIMATION
    # ------------------------------------------------------------------ #
    def _estimate_scale(self, openings, rooms, h, w):
        """Estimate pixels per meter."""
        # 1. Best: Use door width (std door = 0.85-0.95m)
        if openings:
            door_widths = [op["width"] for op in openings if op["type"] == "door"]
            if door_widths:
                median_door_px = float(np.median(door_widths))
                # Ensure the door isn't absurdly small or large
                if 20 < median_door_px < w // 10:
                    return median_door_px / 0.92 
        
        # 2. Fallback: Median room area (~15m2)
        if rooms:
            areas = [r["area_px"] for r in rooms]
            median_area = float(np.median(areas))
            return math.sqrt(median_area) / 3.87

        return max(w, h) / 15.0

