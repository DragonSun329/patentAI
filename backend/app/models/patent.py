"""Patent database models."""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, Index, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector

from app.core.config import settings

Base = declarative_base()


class Claim(Base):
    """Individual patent claim with its own embedding."""
    
    __tablename__ = "claims"
    
    id = Column(String(64), primary_key=True)
    patent_id = Column(String(64), ForeignKey("patents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Claim content
    claim_number = Column(Integer, nullable=False)
    claim_text = Column(Text, nullable=False)
    
    # Claim type analysis
    is_independent = Column(Boolean, default=True)  # Independent vs dependent claim
    parent_claim_number = Column(Integer, nullable=True)  # For dependent claims
    claim_type = Column(String(50), nullable=True)  # method, apparatus, system, composition
    
    # Vector embedding for this specific claim
    embedding = Column(Vector(settings.embed_dimensions), nullable=True)
    
    # Extracted key elements (JSON)
    key_elements = Column(Text, nullable=True)  # JSON array of key technical elements
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    patent = relationship("Patent", back_populates="claim_objects")
    
    __table_args__ = (
        Index(
            'ix_claims_embedding_cosine',
            embedding,
            postgresql_using='ivfflat',
            postgresql_with={'lists': 100},
            postgresql_ops={'embedding': 'vector_cosine_ops'}
        ),
    )


class ClaimComparison(Base):
    """Claim-level comparison results."""
    
    __tablename__ = "claim_comparisons"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    comparison_id = Column(Integer, ForeignKey("comparison_results.id", ondelete="CASCADE"), nullable=False, index=True)
    
    source_claim_id = Column(String(64), ForeignKey("claims.id"), nullable=False)
    target_claim_id = Column(String(64), ForeignKey("claims.id"), nullable=False)
    
    # Similarity scores
    vector_similarity = Column(Float, nullable=True)
    
    # LLM analysis for this claim pair
    overlap_assessment = Column(Text, nullable=True)
    risk_level = Column(String(20), nullable=True)  # low, medium, high
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


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
    
    # Relationships
    claim_objects = relationship("Claim", back_populates="patent", cascade="all, delete-orphan")
    
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
