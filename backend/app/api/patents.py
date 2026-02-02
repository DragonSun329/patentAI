"""Patent API endpoints."""
import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.patent import Patent, ComparisonResult
from app.services.embedding import embedding_service
from app.services.search import search_service, SearchResult
from app.services.llm import llm_service
from app.services.cache import cache_service

router = APIRouter(prefix="/patents", tags=["patents"])


# Request/Response models
class PatentCreate(BaseModel):
    """Patent creation request."""
    title: str = Field(..., min_length=1, max_length=500)
    abstract: str = Field(..., min_length=1)
    claims: Optional[str] = None
    description: Optional[str] = None
    patent_number: Optional[str] = None
    applicant: Optional[str] = None
    inventors: Optional[str] = None
    classification: Optional[str] = None
    filing_date: Optional[datetime] = None


class PatentResponse(BaseModel):
    """Patent response model."""
    id: str
    title: str
    abstract: str
    claims: Optional[str]
    patent_number: Optional[str]
    applicant: Optional[str]
    classification: Optional[str]
    filing_date: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    """Search request."""
    query: str = Field(..., min_length=1)
    limit: int = Field(default=20, ge=1, le=100)
    search_type: str = Field(default="hybrid")  # vector, fuzzy, hybrid
    vector_weight: float = Field(default=0.7, ge=0, le=1)


class SearchResultResponse(BaseModel):
    """Search result item."""
    patent: dict
    vector_score: float
    fuzzy_score: float
    combined_score: float
    match_type: str


class CompareRequest(BaseModel):
    """Patent comparison request."""
    source_patent_id: str
    target_patent_id: str


class CompareResponse(BaseModel):
    """Comparison result."""
    source_patent: dict
    target_patent: dict
    vector_similarity: float
    fuzzy_similarity: float
    combined_score: float
    risk_level: str
    confidence: float
    key_overlaps: List[str]
    differences: List[str]
    explanation: str
    recommendation: str


# Endpoints
@router.post("/", response_model=PatentResponse, status_code=201)
async def create_patent(
    patent: PatentCreate,
    session: AsyncSession = Depends(get_session)
):
    """Create a new patent with embedding."""
    # Generate ID
    patent_id = str(uuid.uuid4())
    
    # Generate embedding
    embedding = await embedding_service.embed_patent(
        patent.title,
        patent.abstract,
        patent.claims
    )
    
    # Create patent record
    db_patent = Patent(
        id=patent_id,
        title=patent.title,
        abstract=patent.abstract,
        claims=patent.claims,
        description=patent.description,
        patent_number=patent.patent_number,
        applicant=patent.applicant,
        inventors=patent.inventors,
        classification=patent.classification,
        filing_date=patent.filing_date,
        embedding=embedding
    )
    
    session.add(db_patent)
    await session.commit()
    await session.refresh(db_patent)
    
    return PatentResponse(
        id=db_patent.id,
        title=db_patent.title,
        abstract=db_patent.abstract,
        claims=db_patent.claims,
        patent_number=db_patent.patent_number,
        applicant=db_patent.applicant,
        classification=db_patent.classification,
        filing_date=str(db_patent.filing_date) if db_patent.filing_date else None,
        created_at=str(db_patent.created_at)
    )


@router.get("/{patent_id}", response_model=PatentResponse)
async def get_patent(
    patent_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get a patent by ID."""
    result = await session.execute(
        select(Patent).where(Patent.id == patent_id)
    )
    patent = result.scalar_one_or_none()
    
    if not patent:
        raise HTTPException(status_code=404, detail="Patent not found")
    
    return PatentResponse(
        id=patent.id,
        title=patent.title,
        abstract=patent.abstract,
        claims=patent.claims,
        patent_number=patent.patent_number,
        applicant=patent.applicant,
        classification=patent.classification,
        filing_date=str(patent.filing_date) if patent.filing_date else None,
        created_at=str(patent.created_at)
    )


@router.post("/search", response_model=List[SearchResultResponse])
async def search_patents(
    request: SearchRequest,
    session: AsyncSession = Depends(get_session)
):
    """Search patents with hybrid vector + fuzzy matching."""
    # Check cache first
    cached = await cache_service.get_search_results(request.query)
    if cached:
        return cached
    
    # Perform search
    results = await search_service.hybrid_search(
        session=session,
        query=request.query,
        limit=request.limit,
        vector_weight=request.vector_weight,
        fuzzy_weight=1 - request.vector_weight
    )
    
    # Format response
    response = [
        SearchResultResponse(
            patent=r.patent,
            vector_score=r.vector_score,
            fuzzy_score=r.fuzzy_score,
            combined_score=r.combined_score,
            match_type=r.match_type
        )
        for r in results
    ]
    
    # Cache results
    await cache_service.set_search_results(
        request.query,
        [r.model_dump() for r in response]
    )
    
    return response


@router.post("/compare", response_model=CompareResponse)
async def compare_patents(
    request: CompareRequest,
    session: AsyncSession = Depends(get_session)
):
    """Compare two patents for potential infringement."""
    # Check cache
    cached = await cache_service.get_analysis(
        request.source_patent_id,
        request.target_patent_id
    )
    if cached:
        return cached
    
    # Get both patents
    source_result = await session.execute(
        select(Patent).where(Patent.id == request.source_patent_id)
    )
    source_patent = source_result.scalar_one_or_none()
    
    target_result = await session.execute(
        select(Patent).where(Patent.id == request.target_patent_id)
    )
    target_patent = target_result.scalar_one_or_none()
    
    if not source_patent or not target_patent:
        raise HTTPException(status_code=404, detail="Patent not found")
    
    # Calculate similarities
    if source_patent.embedding and target_patent.embedding:
        vector_sim = embedding_service.cosine_similarity(
            list(source_patent.embedding),
            list(target_patent.embedding)
        )
    else:
        vector_sim = 0.0
    
    # Fuzzy similarity on text
    from rapidfuzz import fuzz
    source_text = f"{source_patent.title} {source_patent.abstract}"
    target_text = f"{target_patent.title} {target_patent.abstract}"
    fuzzy_sim = fuzz.token_set_ratio(source_text, target_text) / 100.0
    
    combined_score = vector_sim * 0.7 + fuzzy_sim * 0.3
    
    # LLM analysis
    source_dict = {
        "title": source_patent.title,
        "abstract": source_patent.abstract,
        "claims": source_patent.claims
    }
    target_dict = {
        "title": target_patent.title,
        "abstract": target_patent.abstract,
        "claims": target_patent.claims
    }
    
    analysis = await llm_service.analyze_infringement(
        source_dict,
        target_dict,
        combined_score
    )
    
    # Store comparison result
    comparison = ComparisonResult(
        source_patent_id=request.source_patent_id,
        target_patent_id=request.target_patent_id,
        vector_similarity=vector_sim,
        fuzzy_similarity=fuzzy_sim,
        combined_score=combined_score,
        infringement_risk=analysis.get("risk_level", "unknown"),
        llm_explanation=analysis.get("explanation", ""),
        key_overlaps=str(analysis.get("key_overlaps", []))
    )
    session.add(comparison)
    
    response = CompareResponse(
        source_patent=source_dict,
        target_patent=target_dict,
        vector_similarity=vector_sim,
        fuzzy_similarity=fuzzy_sim,
        combined_score=combined_score,
        risk_level=analysis.get("risk_level", "unknown"),
        confidence=analysis.get("confidence", combined_score),
        key_overlaps=analysis.get("key_overlaps", []),
        differences=analysis.get("differences", []),
        explanation=analysis.get("explanation", ""),
        recommendation=analysis.get("recommendation", "")
    )
    
    # Cache result
    await cache_service.set_analysis(
        request.source_patent_id,
        request.target_patent_id,
        response.model_dump()
    )
    
    return response


@router.get("/", response_model=List[PatentResponse])
async def list_patents(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_session)
):
    """List all patents with pagination."""
    result = await session.execute(
        select(Patent).offset(offset).limit(limit)
    )
    patents = result.scalars().all()
    
    return [
        PatentResponse(
            id=p.id,
            title=p.title,
            abstract=p.abstract,
            claims=p.claims,
            patent_number=p.patent_number,
            applicant=p.applicant,
            classification=p.classification,
            filing_date=str(p.filing_date) if p.filing_date else None,
            created_at=str(p.created_at)
        )
        for p in patents
    ]
