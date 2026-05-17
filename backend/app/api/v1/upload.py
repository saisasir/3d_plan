from fastapi import APIRouter, UploadFile, File, HTTPException
import cv2
import numpy as np
from app.cv.preprocessor import FloorPlanPreprocessor
from app.services.intelligence_engine import IntelligenceEngine
import os
import time

router = APIRouter()
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = IntelligenceEngine()
    return _engine

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

SUPPORTED_EXTS = {"jpg", "jpeg", "png", "pdf"}


@router.post("/upload")
async def upload_floor_plan(file: UploadFile = File(...)):
    t0 = time.time()
    filename = file.filename or "unknown"
    ext = filename.split(".")[-1].lower()

    if ext not in SUPPORTED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Accepted: {', '.join(SUPPORTED_EXTS)}"
        )

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 50 MB)")

    # Parse image
    image = None
    try:
        if ext == "pdf":
            image = FloorPlanPreprocessor.process_pdf(content)
        else:
            nparr = np.frombuffer(content, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to decode image: {e}")

    if image is None:
        raise HTTPException(status_code=500, detail="Could not read image data")

    # Run AI pipeline
    try:
        engine = get_engine()
        scene_graph, embedding = await engine.process_full_pipeline(image, filename)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI pipeline error: {e}")

    # Sanitize numpy types for JSON serialization
    def sanitize(obj):
        if isinstance(obj, np.integer):  return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.ndarray):  return obj.tolist()
        if isinstance(obj, dict):        return {k: sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):        return [sanitize(i) for i in obj]
        return obj

    elapsed = round(time.time() - t0, 2)
    print(f"[Upload] Done in {elapsed}s")

    return {
        "message": "Floor plan analyzed successfully",
        "filename": filename,
        "processing_time_s": elapsed,
        "scene_graph": sanitize(scene_graph),
        "embedding": sanitize(embedding),
        "status": "complete",
    }
