"""
IntelligenceEngine — orchestrates the full floor plan → 3D scene pipeline.

Pipeline priority:
  1. Try CubiCasa neural segmentor (if weights present)
  2. Fall back to OpenCV wall detector (always available)
  3. SceneGraphBuilder normalizes and builds the final scene graph
"""
import cv2
import numpy as np
from app.cv.preprocessor import FloorPlanPreprocessor
from app.cv.wall_detector import OpenCVWallDetector
from app.services.scene_builder import SceneGraphBuilder
import os


class IntelligenceEngine:
    def __init__(self):
        self.cv_detector = OpenCVWallDetector()
        self.scene_builder = SceneGraphBuilder()

        # Optional: CubiCasa neural segmentor
        self._neural_ok = False
        try:
            from app.cv.cubicasa_segmentor import CubiCasaSegmentor
            weights = "ai_models/cubicasa_weights.pkl"
            if os.path.exists(weights):
                self.segmentor = CubiCasaSegmentor(weights)
                if self.segmentor.enabled:
                    # FORCIBLY DISABLE NEURAL PIPELINE:
                    # The neural model completely hallucinates on American grid blueprints.
                    # We will force the system to use the highly tuned OpenCV pipeline.
                    self._neural_ok = False
                    print("[IntelligenceEngine] CubiCasa weights found, but forcing OpenCV for grid blueprints")
                else:
                    print("[IntelligenceEngine] CubiCasa weights found but model not enabled")
            else:
                print("[IntelligenceEngine] CubiCasa weights not found — using OpenCV pipeline")
        except Exception as e:
            print(f"[IntelligenceEngine] Neural model unavailable ({e}) — using OpenCV pipeline")

        # Optional: YOLOv8 symbol detector
        self._yolo_ok = False
        try:
            from app.cv.detector import FloorPlanDetector
            yolo_weights = "ai_models/best.pt"
            if os.path.exists(yolo_weights):
                self.symbol_detector = FloorPlanDetector(yolo_weights)
                self._yolo_ok = True
                print("[IntelligenceEngine] YOLOv8 symbol detector loaded OK")
        except Exception as e:
            print(f"[IntelligenceEngine] YOLOv8 unavailable ({e})")

        # Optional: OCR for room labels
        self._ocr_ok = False
        try:
            from app.services.ocr_service import OCRService
            self.ocr = OCRService()
            self._ocr_ok = True
            print("[IntelligenceEngine] OCR service loaded OK")
        except Exception as e:
            print(f"[IntelligenceEngine] OCR unavailable ({e})")

    async def process_full_pipeline(self, image: np.ndarray, filename: str):
        print(f"\n{'='*50}")
        print(f"[Pipeline] Processing: {filename}  shape={image.shape}")

        # Stage 1: Preprocess
        image = self._safe_resize(image, max_size=1024)
        straightened = FloorPlanPreprocessor.deskew(image)
        print(f"[Stage 1] Deskew complete. Shape: {straightened.shape}")

        # Stage 2: Room & Wall Detection
        cv_result = None

        if self._neural_ok:
            try:
                cv_result = self._run_neural_pipeline(straightened)
                
                # Hallucination check: 
                # If the AI hallucinates too many unique room types (e.g., predicting 15+ different classes),
                # or finds an absurd number of rooms for a single floor plan, it is severely confused.
                num_rooms = len(cv_result.get("rooms", []))
                
                # We can count unique classes from the rooms
                unique_found = len(set([r.get("type") for r in cv_result.get("rooms", [])]))
                
                if cv_result and num_rooms >= 3 and unique_found <= 10 and num_rooms < 50:
                    print(f"[Stage 2] Neural: {num_rooms} rooms (Classes: {unique_found})")
                else:
                    print(f"[Stage 2] Neural hallucinated {num_rooms} rooms across {unique_found} classes, rejecting AI result.")
                    cv_result = None
            except Exception as e:
                print(f"[Stage 2] Neural failed ({e}), using OpenCV")
                cv_result = None

        if not cv_result or len(cv_result.get("rooms", [])) == 0:
            cv_result = self.cv_detector.analyze(straightened)
            print(f"[Stage 2] OpenCV: {len(cv_result['rooms'])} rooms, {len(cv_result['walls'])} walls")

        # Stage 3: YOLO symbols (optional — add detected openings)
        if self._yolo_ok:
            try:
                symbols = self.symbol_detector.detect_symbols(straightened)
                detected_openings = []
                for sym in symbols:
                    if sym["class"] in ["door", "window"]:
                        detected_openings.append({
                            "type": sym["class"],
                            "position": sym["center"],
                            "width": abs(sym["bbox"][2] - sym["bbox"][0]),
                            "rotation": 0.0,
                        })
                if detected_openings:
                    cv_result["openings"] = detected_openings
                    print(f"[Stage 3] YOLO: {len(detected_openings)} openings detected")
            except Exception as e:
                print(f"[Stage 3] YOLO failed: {e}")

        # Stage 4: OCR labels (optional — use text to label rooms)
        if self._ocr_ok and cv_result.get("rooms"):
            try:
                cv_result["rooms"] = self.ocr.extract_room_labels(straightened, cv_result["rooms"])
                print(f"[Stage 4] OCR: room labels extracted")
            except Exception as e:
                print(f"[Stage 4] OCR failed: {e}")

        # Stage 5: Build normalized scene graph
        scene_graph = self.scene_builder.build(cv_result, wall_height=2.7, filename=filename)

        print(f"[Stage 5] Built: {len(scene_graph['rooms'])} rooms, "
              f"{len(scene_graph['walls'])} walls, "
              f"{len(scene_graph['openings'])} openings, "
              f"{len(scene_graph['furniture'])} furniture")

        embedding = self._compute_embedding(scene_graph)
        return scene_graph, embedding

    def _run_neural_pipeline(self, image: np.ndarray) -> dict:
        from app.geometry.polygonizer import GeometryPolygonizer
        h, w = image.shape[:2]
        cubi = self.segmentor.predict(image)
        room_mask = cubi["room_mask"]
        unique_classes, counts = np.unique(room_mask, return_counts=True)
        bg_class = unique_classes[np.argmax(counts)]
        rooms = []
        for class_idx in unique_classes:
            if class_idx == bg_class:
                continue
            polys = self.segmentor.get_polygons_from_mask(room_mask, class_idx)
            for poly in polys:
                clean = GeometryPolygonizer.clean_room_polygon(poly)
                rooms.append({
                    "id": f"room_{len(rooms)}",
                    "type": f"class_{class_idx}",
                    "name": f"Room {len(rooms)+1}",
                    "polygon": clean,
                    "area_px": len(poly),
                })
        return {"rooms": rooms, "walls": [], "openings": [],
                "scale_factor": w / 15.0, "image_dims": {"w": w, "h": h}}

    def _safe_resize(self, image: np.ndarray, max_size: int = 1024) -> np.ndarray:
        h, w = image.shape[:2]
        if max(h, w) <= max_size:
            return image
        scale = max_size / max(h, w)
        return cv2.resize(image, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)

    def _compute_embedding(self, scene_graph: dict) -> list:
        meta = scene_graph.get("metadata", {})
        features = [
            meta.get("width_m", 0), meta.get("depth_m", 0),
            float(len(scene_graph.get("rooms", []))),
            float(len(scene_graph.get("walls", []))),
            float(len(scene_graph.get("openings", []))),
        ] + [0.0] * 11
        norm = np.linalg.norm(features)
        if norm > 0:
            features = (np.array(features) / norm).tolist()
        return features
