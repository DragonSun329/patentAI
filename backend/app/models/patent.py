"""Patent database models."""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, Index
from sqlalchemy.orm import declarative_base
from pgvector.sqlalchemy import Vector

from app.core.config import settings

Base = declarative_base()


class Patent(Base):
    """Patent document with vector embedding."""
    
    __tablename__ = "patents"
    
    id = Column(String(64), primary_key=True)
    title = Column(String(500), nullable=False, index=True)
    abstract = Column(Text, nullable=False)
    claims = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    
    # Metadata
    patent_number = Column(String(50), unique=True, index=True)
    filing_date = Column(DateTime, nullable=True)
    publication_date = Column(DateTime, nullable=True)
    applicant = Column(String(500), nullable=True)
    inventors = Column(Text, nullable=True)  # JSON array
    classification = Column(String(100), nullable=True)  # IPC/CPC code
    
    # Vector embedding (nomic-embed-text = 768 dims)
    embedding = Column(Vector(settings.embed_dimensions), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for vector search
    __table_args__ = (
        Index(
            'ix_patents_embedding_cosine',
            embedding,
            postgresql_using='ivfflat',
            postgresql_with={'lists': 100},
            postgresql_ops={'embedding': 'vector_cosine_ops'}
        ),
    )


class SearchHistory(Base):
    """Track search queries for analytics."""
    
    __tablename__ = "search_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query_text = Column(Text, nullable=False)
    query_type = Column(String(50), default="semantic")  # semantic, fuzzy, hybrid
    results_count = Column(Integer, default=0)
    top_score = Column(Float, nullable=True)
    latency_ms = Column(Float, nullable=True)
    user_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ComparisonResult(Base):
    """Store patent comparison results."""
    
    __tablename__ = "comparison_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_patent_id = Column(String(64), nullable=False, index=True)
    target_patent_id = Column(String(64), nullable=False, index=True)
    
    # Similarity scores
    vector_similarity = Column(Float, nullable=True)
    fuzzy_similarity = Column(Float, nullable=True)
    combined_score = Column(Float, nullable=True)
    
    # LLM analysis
    infringement_risk = Column(String(20), nullable=True)  # low, medium, high
    llm_explanation = Column(Text, nullable=True)
    key_overlaps = Column(Text, nullable=True)  # JSON array
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
