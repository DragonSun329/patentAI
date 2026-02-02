"""Claims API endpoints."""
from typing import List, Optional
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.patent import Claim, Patent
from app.services.claim_service import claim_service, ClaimMatch


router = APIRouter(prefix="/claims", tags=["claims"])


# Response models
class ClaimResponse(BaseModel):
    """Individual claim response."""
    id: str
    patent_id: str
    claim_number: int
    claim_text: str
    is_independent: bool
    parent_claim_number: Optional[int]
    claim_type: Optional[str]
    key_elements: List[str] = []


class ClaimMatchResponse(BaseModel):
    """Claim match in comparison."""
    source_claim: dict
    target_claim: dict
    similarity: float
    risk_level: str
    overlap_assessment: Optional[str]


class ClaimComparisonResponse(BaseModel):
    """Full claim-level comparison result."""
    source_patent_id: str
    target_patent_id: str
    source_claims_count: int
    target_claims_count: int
    top_matches: List[ClaimMatchResponse]
    highest_similarity: float
    average_similarity: float
    independent_claims_at_risk: int
    overall_risk: str
    summary: str
    recommendation: str


class SimilarClaimResponse(BaseModel):
    """Similar claim search result."""
    claim_id: str
    patent_id: str
    claim_number: int
    claim_text: str
    is_independent: bool
    claim_type: Optional[str]
    patent_title: str
    patent_number: Optional[str]
    similarity: float


class ProcessClaimsRequest(BaseModel):
    """Request to process claims for a patent."""
    patent_id: str


class SearchClaimsRequest(BaseModel):
    """Request to search for similar claims."""
    claim_text: str = Field(..., min_length=10)
    limit: int = Field(default=10, ge=1, le=50)
    exclude_patent_id: Optional[str] = None


class CompareClaimsRequest(BaseModel):
    """Request for claim-level comparison."""
    source_patent_id: str
    target_patent_id: str
    include_llm_analysis: bool = True


# Endpoints
@router.post("/process", response_model=List[ClaimResponse])
async def process_patent_claims(
    request: ProcessClaimsRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Parse and embed claims for a patent.
    This extracts individual claims from the patent's claims text,
    analyzes them (independent vs dependent, claim type), and 
    generates embeddings for each.
    """
    claims = await claim_service.process_patent_claims(session, request.patent_id)
    
    if not claims:
        raise HTTPException(
            status_code=404, 
            detail="Patent not found or has no claims to process"
        )
    
    return [
        ClaimResponse(
            id=c.id,
            patent_id=c.patent_id,
            claim_number=c.claim_number,
            claim_text=c.claim_text,
            is_independent=c.is_independent,
            parent_claim_number=c.parent_claim_number,
            claim_type=c.claim_type,
            key_elements=[]
        )
        for c in claims
    ]


@router.get("/patent/{patent_id}", response_model=List[ClaimResponse])
async def get_patent_claims(
    patent_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get all parsed claims for a patent."""
    claims = await claim_service.get_patent_claims(session, patent_id)
    
    import json
    return [
        ClaimResponse(
            id=c.id,
            patent_id=c.patent_id,
            claim_number=c.claim_number,
            claim_text=c.claim_text,
            is_independent=c.is_independent,
            parent_claim_number=c.parent_claim_number,
            claim_type=c.claim_type,
            key_elements=json.loads(c.key_elements) if c.key_elements else []
        )
        for c in claims
    ]


@router.post("/compare", response_model=ClaimComparisonResponse)
async def compare_patent_claims(
    request: CompareClaimsRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Perform claim-level comparison between two patents.
    
    This is the core infringement analysis - it:
    1. Parses claims from both patents (if not already done)
    2. Compares each claim pair using vector similarity
    3. Identifies the highest-risk claim overlaps
    4. Uses LLM to provide detailed analysis of top matches
    """
    result = await claim_service.compare_claims(
        session=session,
        source_patent_id=request.source_patent_id,
        target_patent_id=request.target_patent_id,
        include_llm_analysis=request.include_llm_analysis
    )
    
    return ClaimComparisonResponse(
        source_patent_id=result.source_patent_id,
        target_patent_id=result.target_patent_id,
        source_claims_count=result.source_claims_count,
        target_claims_count=result.target_claims_count,
        top_matches=[
            ClaimMatchResponse(
                source_claim=m.source_claim,
                target_claim=m.target_claim,
                similarity=m.similarity,
                risk_level=m.risk_level,
                overlap_assessment=m.overlap_assessment
            )
            for m in result.top_matches
        ],
        highest_similarity=result.highest_similarity,
        average_similarity=result.average_similarity,
        independent_claims_at_risk=result.independent_claims_at_risk,
        overall_risk=result.overall_risk,
        summary=result.summary,
        recommendation=result.recommendation
    )


@router.post("/search", response_model=List[SimilarClaimResponse])
async def search_similar_claims(
    request: SearchClaimsRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Find claims similar to given text across all patents.
    
    Useful for:
    - Prior art search at the claim level
    - Finding patents that might be infringed by a proposed claim
    - Understanding the patent landscape for a specific technology
    """
    results = await claim_service.find_similar_claims(
        session=session,
        claim_text=request.claim_text,
        limit=request.limit,
        exclude_patent_id=request.exclude_patent_id
    )
    
    return [
        SimilarClaimResponse(**r)
        for r in results
    ]


@router.get("/{claim_id}", response_model=ClaimResponse)
async def get_claim(
    claim_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get a specific claim by ID."""
    result = await session.execute(
        select(Claim).where(Claim.id == claim_id)
    )
    claim = result.scalar_one_or_none()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    import json
    return ClaimResponse(
        id=claim.id,
        patent_id=claim.patent_id,
        claim_number=claim.claim_number,
        claim_text=claim.claim_text,
        is_independent=claim.is_independent,
        parent_claim_number=claim.parent_claim_number,
        claim_type=claim.claim_type,
        key_elements=json.loads(claim.key_elements) if claim.key_elements else []
    )
