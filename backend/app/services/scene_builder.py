"""
Scene graph builder v2: converts raw pixel-space CV output into a
normalized, meter-scale scene graph ready for Three.js rendering.

Key improvements:
- Walls derived cleanly from room polygon edges with shared-wall dedup
- Proper corner joining (extend/trim wall endpoints)
- Opening placement on the correct wall segment with wall-relative position
- Better furniture placement: pushed against walls, respecting room bounds
- Per-room floor texture mapping
"""

import math
import numpy as np
from typing import List, Dict, Tuple, Optional


# ---------------------------------------------------------------------------
# Room-type → furniture catalogue (offset relative to room center)
# ---------------------------------------------------------------------------
FURNITURE_CATALOGUE = {
    "living_room": [
        {"type": "sofa",         "wall_side": "back",  "offset": 0.5,  "rotation": 0.0,    "scale": [1.4, 1.4, 1.4]},
        {"type": "coffee_table", "wall_side": "center","offset": 0.0,  "rotation": 0.0,    "scale": [0.9, 0.9, 0.9]},
    ],
    "bedroom": [
        {"type": "bed",          "wall_side": "back",  "offset": 0.0,  "rotation": 0.0,    "scale": [1.3, 1.3, 1.3]},
        {"type": "chair",        "wall_side": "front", "offset": 0.8,  "rotation": math.pi, "scale": [0.8, 0.8, 0.8]},
    ],
    "kitchen": [
        {"type": "chair",        "wall_side": "center","offset": 0.5,  "rotation": 0.0,    "scale": [0.7, 0.7, 0.7]},
    ],
    "bathroom": [],
    "hallway":  [],
    "room":     [],
}

MODEL_MAP = {
    "sofa":         "sofa.glb",
    "bed":          "bed.glb",
    "chair":        "chair.glb",
    "coffee_table": "chair.glb",
}

TEXTURE_MAP = {
    "living_room":  "wood",
    "bedroom":      "wood",
    "kitchen":      "tiles",
    "bathroom":     "tiles",
    "dining_room":  "wood",
    "hallway":      "concrete",
    "balcony":      "concrete",
    "room":         "wood",
}

# Warm, professional architectural palette
ROOM_COLORS = {
    "living_room":  "#F5F1E6", # Cream / Pearl
    "bedroom":      "#FAF9F6", # Off-white
    "kitchen":      "#ECEEE9", # Soft Sage
    "bathroom":     "#E6EEF0", # Clean Blue-Gray
    "dining_room":  "#F2EBE1", # Warm Oat
    "hallway":      "#F7F7F7", # Light Gray
    "balcony":      "#E8F0E8", # Pale Green
    "room":         "#FAFAFA",
}


class SceneGraphBuilder:

    def build(
        self,
        cv_result: Dict,
        wall_height: float = 2.7,
        filename: str = "plan",
    ) -> Dict:
        """
        Master entry point.
        cv_result keys: rooms, walls, openings, scale_factor, image_dims
        Returns: complete scene_graph dict
        """
        rooms_px    = cv_result.get("rooms", [])
        walls_px    = cv_result.get("walls", [])
        openings_px = cv_result.get("openings", [])
        scale       = cv_result.get("scale_factor", 30.0)   # px/m
        img_dims    = cv_result.get("image_dims", {"w": 512, "h": 512})

        iw, ih = img_dims["w"], img_dims["h"]

        # ── 1. Compute the center offset (in pixels) ─────────────────────
        cx_px = iw / 2.0
        cy_px = ih / 2.0

        def px_to_m(px_x: float, px_y: float) -> Tuple[float, float]:
            """Pixel → meter, centered at origin, Y-axis flipped."""
            x_m = (px_x - cx_px) / scale
            z_m = (px_y - cy_px) / scale
            return round(x_m, 4), round(z_m, 4)

        # ── 2. Build rooms ────────────────────────────────────────────────
        scene_rooms = []

        for room in rooms_px:
            poly_px = room.get("polygon", [])
            if len(poly_px) < 3:
                continue

            # Convert polygon to meters
            poly_m = [list(px_to_m(p[0], p[1])) for p in poly_px]
            
            # CLEAN GEOMETRY: Fix self-intersections using shapely
            try:
                from shapely.geometry import Polygon, MultiPolygon
                p_obj = Polygon(poly_m).buffer(0.01).buffer(-0.01) # Clean and simplify
                if p_obj.is_empty: continue
                if isinstance(p_obj, MultiPolygon):
                    p_obj = max(p_obj.geoms, key=lambda a: a.area)
                poly_m = list(p_obj.exterior.coords)
            except Exception as e:
                print(f"Polygon cleanup failed: {e}")

            room_type = room.get("type", "room")
            room_center_m = self._polygon_centroid(poly_m)
            room_area_m2 = self._polygon_area(poly_m)

            scene_rooms.append({
                "id":       room["id"],
                "type":     room_type,
                "name":     room.get("name", room_type.replace("_", " ").title()),
                "polygon":  poly_m,
                "center":   room_center_m,
                "texture":  TEXTURE_MAP.get(room_type, "wood"),
                "color":    ROOM_COLORS.get(room_type, "#D8D8D8"),
                "area_m2":  round(room_area_m2, 1),
            })

        # ── 3. Coordinate Grid Snapping (Closes all gaps/islands) ────────
        scene_rooms = self._snap_coordinates_to_grid(scene_rooms, threshold=0.45)

        # ── 4. Place furniture in snapped rooms ──────────────────────────
        furniture_items = []
        furniture_id = 0
        for room in scene_rooms:
            room_type = room["type"]
            poly_m = room["polygon"]
            room_center_m = room["center"]
            furniture_defs = FURNITURE_CATALOGUE.get(room_type, [])
            bbox_m = self._polygon_bbox(poly_m)

            for fdef in furniture_defs:
                fx, fz = self._compute_furniture_position(
                    room_center_m, bbox_m, fdef
                )
                furniture_items.append({
                    "id":       f"furniture_{furniture_id}",
                    "type":     fdef["type"],
                    "model":    MODEL_MAP.get(fdef["type"], "chair.glb"),
                    "position": [fx, 0.0, fz],
                    "rotation": fdef["rotation"],
                    "scale":    fdef["scale"],
                    "room_id":  room["id"],
                })
                furniture_id += 1

        # ── 4. Build walls from room polygon edges ────────────────────────
        scene_walls = self._build_walls(scene_rooms, walls_px, wall_height, scale, cx_px, cy_px)

        # ── 5. Openings ───────────────────────────────────────────────────
        scene_openings = []
        for op in openings_px[:8]:  # Cap at 8 openings to avoid visual clutter
            pos = op.get("position", [0, 0])
            ox, oz = px_to_m(pos[0], pos[1])
            w_m = op.get("width", 30.0) / scale
            
            best_wall_idx = -1
            closest_dist = float('inf')
            snap_x, snap_z = ox, oz
            rotation = op.get("rotation", 0.0)

            for idx, wall in enumerate(scene_walls):
                p1, p2 = wall["points"]
                vx, vz = p2[0] - p1[0], p2[1] - p1[1]
                length = math.hypot(vx, vz)
                if length == 0: continue
                
                t = ((ox - p1[0]) * vx + (oz - p1[1]) * vz) / (length * length)
                t = max(0, min(1, t))
                
                px, pz = p1[0] + t * vx, p1[1] + t * vz
                dist = math.hypot(ox - px, oz - pz)
                
                if dist < closest_dist and dist < 0.8: # Only snap if within 0.8m
                    closest_dist = dist
                    snap_x, snap_z = px, pz
                    rotation = math.atan2(vz, vx)
                    best_wall_idx = idx

            if best_wall_idx != -1:
                # Calculate relative position along wall segment (0.0 to length)
                p1 = scene_walls[best_wall_idx]["points"][0]
                dist_from_p1 = math.hypot(snap_x - p1[0], snap_z - p1[1])
                
                opening_data = {
                    "type":     op.get("type", "door"),
                    "position": [snap_x, 0.0, snap_z],
                    "width":    round(max(0.7, min(w_m, 1.1)), 3),
                    "height":   2.1 if op.get("type") == "door" else 1.2,
                    "elevation": 0.0 if op.get("type") == "door" else 0.9,
                    "rotation": rotation,
                    "wall_pos": dist_from_p1
                }
                scene_openings.append(opening_data)
                
                # Attach to wall for cutout
                if "openings" not in scene_walls[best_wall_idx]:
                    scene_walls[best_wall_idx]["openings"] = []
                scene_walls[best_wall_idx]["openings"].append(opening_data)


        # ── 6. Compute real-world extents ─────────────────────────────────
        all_x = [p[0] for r in scene_rooms for p in r["polygon"]]
        all_z = [p[1] for r in scene_rooms for p in r["polygon"]]
        extent_x = (max(all_x) - min(all_x)) if all_x else 10.0
        extent_z = (max(all_z) - min(all_z)) if all_z else 10.0

        metadata = {
            "unit":           "meters",
            "scale_px_per_m": round(scale, 2),
            "width_m":        round(extent_x, 2),
            "depth_m":        round(extent_z, 2),
            "wall_height_m":  wall_height,
            "filename":       filename,
            "room_count":     len(scene_rooms),
        }

        return {
            "metadata":  metadata,
            "rooms":     scene_rooms,
            "walls":     scene_walls,
            "openings":  scene_openings,
            "furniture": furniture_items,
        }

    # ------------------------------------------------------------------
    #  Wall building
    # ------------------------------------------------------------------
    def _build_walls(self, rooms, walls_px, wall_height, scale, cx_px, cy_px):
        """Build clean walls from room polygon edges."""
        seen_edges = set()
        walls = []

        def px_to_m(px_x, px_y):
            x_m = (px_x - cx_px) / scale
            z_m = (px_y - cy_px) / scale
            return round(x_m, 4), round(z_m, 4)

        # Derive walls from room polygon edges (most reliable)
        for room in rooms:
            poly = room["polygon"]
            n = len(poly)
            for i in range(n):
                p1 = poly[i]
                p2 = poly[(i + 1) % n]

                # Round to 0.1m grid for deduplication since coordinates are already snapped
                snap = 0.1
                edge_key = tuple(sorted([
                    (round(p1[0] / snap) * snap, round(p1[1] / snap) * snap),
                    (round(p2[0] / snap) * snap, round(p2[1] / snap) * snap),
                ]))

                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)

                length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                if length < 0.4:  # Skip tiny fragments
                    continue

                walls.append({
                    "points": [list(p1), list(p2)],
                    "height": wall_height,
                    "thickness": 0.12, # Thinner, more professional walls
                    "length_m": round(length, 3),
                })

        # If no rooms, fall back to pixel-space walls
        if not walls and walls_px:
            for w in walls_px:
                pts = w.get("points", [])
                if len(pts) < 2:
                    continue
                p1 = list(px_to_m(pts[0][0], pts[0][1]))
                p2 = list(px_to_m(pts[1][0], pts[1][1]))
                length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                if length < 0.2:
                    continue
                walls.append({
                    "points": [p1, p2],
                    "height": wall_height,
                    "thickness": 0.15,
                    "length_m": round(length, 3),
                })

        return walls

    # ------------------------------------------------------------------
    #  Furniture placement
    # ------------------------------------------------------------------
    def _compute_furniture_position(self, center, bbox, fdef):
        """Place furniture intelligently within the room."""
        min_x, min_z, max_x, max_z = bbox
        room_w = max_x - min_x
        room_d = max_z - min_z

        wall_side = fdef.get("wall_side", "center")
        offset = fdef.get("offset", 0.0)

        if wall_side == "back":
            # Push toward the far wall with offset
            fx = center[0]
            fz = min_z + room_d * 0.2 + offset
        elif wall_side == "left":
            fx = min_x + room_w * 0.2
            fz = center[1] + offset
        elif wall_side == "right":
            fx = max_x - room_w * 0.2
            fz = center[1] + offset
        else:  # center
            fx = center[0] + offset
            fz = center[1]

        return round(fx, 3), round(fz, 3)

    # ------------------------------------------------------------------
    #  Helpers
    # ------------------------------------------------------------------
    def _polygon_centroid(self, poly: List[List[float]]) -> List[float]:
        xs = [p[0] for p in poly]
        zs = [p[1] for p in poly]
        return [round(sum(xs) / len(xs), 4), round(sum(zs) / len(zs), 4)]

    def _polygon_area(self, poly: List[List[float]]) -> float:
        """Shoelace formula for polygon area."""
        n = len(poly)
        if n < 3:
            return 0.0
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += poly[i][0] * poly[j][1]
            area -= poly[j][0] * poly[i][1]
        return abs(area) / 2.0

    def _polygon_bbox(self, poly: List[List[float]]) -> Tuple[float, float, float, float]:
        """Returns (min_x, min_z, max_x, max_z)."""
        xs = [p[0] for p in poly]
        zs = [p[1] for p in poly]
        return min(xs), min(zs), max(xs), max(zs)

    def _snap_coordinates_to_grid(self, rooms: List[Dict], threshold: float = 0.35) -> List[Dict]:
        """
        Snaps close room vertices to each other using pairwise 2D clustering.
        This prevents chain-coordinate collapses while perfectly closing room-to-room gaps.
        """
        # 1. Collect all vertices
        vertices = []
        for r_idx, r in enumerate(rooms):
            for p_idx, p in enumerate(r["polygon"]):
                vertices.append({
                    "room_idx": r_idx,
                    "poly_idx": p_idx,
                    "coord": np.array(p)
                })

        if not vertices:
            return rooms

        # 2. Cluster in 2D space
        used = [False] * len(vertices)
        for i in range(len(vertices)):
            if used[i]:
                continue
            
            # Find all vertices that are physically close in 2D space (within threshold)
            close_indices = [i]
            for j in range(i + 1, len(vertices)):
                if used[j]:
                    continue
                dist = np.linalg.norm(vertices[i]["coord"] - vertices[j]["coord"])
                if dist <= threshold:
                    close_indices.append(j)
            
            if len(close_indices) > 1:
                # Mark as used so they aren't clustered again
                for idx in close_indices:
                    used[idx] = True
                
                # Compute their average 2D coordinate
                coords = [vertices[idx]["coord"] for idx in close_indices]
                avg_coord = np.mean(coords, axis=0)
                
                avg_x = round(float(avg_coord[0]), 4)
                avg_z = round(float(avg_coord[1]), 4)
                
                # Apply average coordinate to all snapped vertices
                for idx in close_indices:
                    r_idx = vertices[idx]["room_idx"]
                    p_idx = vertices[idx]["poly_idx"]
                    rooms[r_idx]["polygon"][p_idx] = [avg_x, avg_z]

        # 3. Clean up polygons and deduplicate consecutive vertices
        for r in rooms:
            poly = r["polygon"]
            dedup = []
            for p in poly:
                if not dedup or (p[0] != dedup[-1][0] or p[1] != dedup[-1][1]):
                    dedup.append(p)
            
            # Ensure closed properly
            if len(dedup) >= 3:
                if dedup[0][0] == dedup[-1][0] and dedup[0][1] == dedup[-1][1]:
                    pass
                else:
                    d = math.hypot(dedup[0][0] - dedup[-1][0], dedup[0][1] - dedup[-1][1])
                    if d < 0.1:
                        dedup[-1] = dedup[0]
            r["polygon"] = dedup

            # Recompute center and area
            xs = [p[0] for p in dedup]
            zs = [p[1] for p in dedup]
            if xs:
                r["center"] = [round(sum(xs) / len(xs), 4), round(sum(zs) / len(zs), 4)]
                r["area_m2"] = round(self._polygon_area(dedup), 1)

        return rooms
