from sqlalchemy import String, Integer, ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.db.base_class import Base
from datetime import datetime

class Scene(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    vendor_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=True)
    
    # Store the entire Scene Graph JSON here
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # AI Embedding for similarity search
    embedding: Mapped[list] = mapped_column(Vector(384), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
