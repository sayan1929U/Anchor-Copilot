from sqlalchemy import Column, Integer, String, Text, DateTime, func
from pgvector.sqlalchemy import Vector
from app.database import Base

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)       # e.g. "remote_work_policy.md"
    category = Column(String, nullable=False)      # matches agent domains: stability, pathways, etc.
    content = Column(Text, nullable=False)          # the actual chunk text
    embedding = Column(Vector(384), nullable=False) # 384 = output dim of all-MiniLM-L6-v2
    created_at = Column(DateTime(timezone=True), server_default=func.now())
