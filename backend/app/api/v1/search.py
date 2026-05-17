from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.api import deps
from app.models.scene import Scene
from app.db.session import get_db
from pgvector.sqlalchemy import Vector
from typing import List

router = APIRouter()

@router.get("/similar/{scene_id}")
async def get_similar_scenes(
    scene_id: int,
    limit: int = 5,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user)
):
    """
    Finds floor plans with similar architectural DNA using pgvector cosine similarity.
    """
    # 1. Get the embedding of the source scene
    source_scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not source_scene or source_scene.embedding is None:
        raise HTTPException(status_code=404, detail="Scene or embedding not found")
    
    # 2. Perform Vector Search (Cosine Distance)
    # <-> is Euclidean distance, <=> is Cosine distance in pgvector
    similar_scenes = db.query(Scene).filter(Scene.id != scene_id).order_by(
        Scene.embedding.cosine_distance(source_scene.embedding)
    ).limit(limit).all()
    
    return [
        {
            "id": s.id,
            "name": s.data.get("metadata", {}).get("name", "Unnamed Plan"),
            "match_score": 1 - (s.embedding.cosine_distance(source_scene.embedding)) if s.embedding else 0
        }
        for s in similar_scenes
    ]
