"""Prior Art Search API - Find patents that might block your invention."""
import uuid
from typing import List, Optional
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.patent import Patent, Claim
from app.services.embedding import embedding_service
from app.services.llm import llm_service
from app.services.claim_service import claim_service


router = APIRouter(prefix="/priorart", tags=["prior-art"])


# Request/Response models
class PriorArtSearchRequest(BaseModel):
    """Prior art search request."""
    invention_description: str = Field(
        ..., 
        min_length=50,
        description="Describe your invention in detail (min 50 chars)"
    )
    technology_area: Optional[str] = Field(
        None,
        description="Optional: CPC code or technology keywords to narrow search"
    )
    limit: int = Field(default=20, ge=1, le=50)
    include_analysis: bool = Field(default=True, description="Include LLM risk analysis")


class BlockingClaim(BaseModel):
    """A potentially blocking claim."""
    claim_id: str
    patent_id: str
    patent_number: Optional[str]
    patent_title: str
    claim_number: int
    claim_text: str
    is_independent: bool
    similarity: float
    risk_level: str  # low, medium, high


class BlockingPatent(BaseModel):
    """A patent with potentially blocking claims."""
    patent_id: str
    patent_number: Optional[str]
    title: str
    abstract: str
    applicant: Optional[str]
    publication_date: Optional[str]
    blocking_claims: List[BlockingClaim]
    highest_similarity: float
    overall_risk: str


class PriorArtAnalysis(BaseModel):
    """LLM analysis of prior art risk."""
    freedom_to_operate: str  # likely, uncertain, unlikely
    key_risks: List[str]
    design_around_suggestions: List[str]
    recommendation: str


class PriorArtSearchResponse(BaseModel):
    """Prior art search results."""
    query_summary: str
    total_patents_searched: int
    blocking_patents_found: int
    patents: List[BlockingPatent]
    analysis: Optional[PriorArtAnalysis]


# Endpoints
@router.post("/search", response_model=PriorArtSearchResponse)
async def search_prior_art(
    request: PriorArtSearchRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Search for prior art that might block your invention.
    
    Describe your invention and we'll find:
    1. Similar patents at the claim level
    2. Specific claims that might be blocking
    3. Risk assessment and design-around suggestions
    """
    # Get embedding for the invention description
    invention_embedding = await embedding_service.embed_text(request.invention_description)
    
    # Search claims by vector similarity
    sql = text("""
        SELECT 
            c.id as claim_id,
            c.patent_id,
            c.claim_number,
            c.claim_text,
            c.is_independent,
            c.claim_type,
            p.title as patent_title,
            p.patent_number,
            p.abstract,
            p.applicant,
            p.publication_date,
            1 - (c.embedding <=> :embedding) as similarity
        FROM claims c
        JOIN patents p ON c.patent_id = p.id
        WHERE c.embedding IS NOT NULL
        ORDER BY c.embedding <=> :embedding
        LIMIT :limit
    """)
    
    result = await session.execute(
        sql,
        {"embedding": str(invention_embedding), "limit": request.limit * 3}
    )
    rows = result.fetchall()
    
    # Get total patent count for context
    count_result = await session.execute(select(Patent.id))
    total_patents = len(count_result.fetchall())
    
    # Group by patent and calculate risk
    patent_map = {}
    for row in rows:
        patent_id = row[1]
        similarity = float(row[11]) if row[11] else 0.0
        
        # Determine claim risk level
        if similarity >= 0.75:
            risk = "high"
        elif similarity >= 0.55:
            risk = "medium"
        else:
            risk = "low"
        
        claim = BlockingClaim(
            claim_id=row[0],
            patent_id=patent_id,
            patent_number=row[7],
            patent_title=row[6],
            claim_number=row[2],
            claim_text=row[3],
            is_independent=row[4],
            similarity=similarity,
            risk_level=risk
        )
        
        if patent_id not in patent_map:
            patent_map[patent_id] = {
                "patent_id": patent_id,
                "patent_number": row[7],
                "title": row[6],
                "abstract": row[8],
                "applicant": row[9],
                "publication_date": str(row[10]) if row[10] else None,
                "blocking_claims": [],
                "highest_similarity": 0.0
            }
        
        patent_map[patent_id]["blocking_claims"].append(claim)
        if similarity > patent_map[patent_id]["highest_similarity"]:
            patent_map[patent_id]["highest_similarity"] = similarity
    
    # Convert to list and sort by highest similarity
    patents = []
    for p in patent_map.values():
        # Only include patents with meaningful similarity
        if p["highest_similarity"] >= 0.4:
            # Determine overall patent risk
            if p["highest_similarity"] >= 0.75:
                overall_risk = "high"
            elif p["highest_similarity"] >= 0.55:
                overall_risk = "medium"
            else:
                overall_risk = "low"
            
            # Sort claims by similarity
            p["blocking_claims"].sort(key=lambda c: c.similarity, reverse=True)
            # Keep top 5 claims per patent
            p["blocking_claims"] = p["blocking_claims"][:5]
            
            patents.append(BlockingPatent(
                **{k: v for k, v in p.items() if k != "highest_similarity"},
                highest_similarity=p["highest_similarity"],
                overall_risk=overall_risk
            ))
    
    patents.sort(key=lambda p: p.highest_similarity, reverse=True)
    patents = patents[:request.limit]
    
    # LLM Analysis
    analysis = None
    if request.include_analysis and patents:
        analysis = await _analyze_prior_art(
            request.invention_description,
            patents[:5]  # Analyze top 5
        )
    
    # Generate query summary
    query_summary = request.invention_description[:200]
    if len(request.invention_description) > 200:
        query_summary += "..."
    
    return PriorArtSearchResponse(
        query_summary=query_summary,
        total_patents_searched=total_patents,
        blocking_patents_found=len(patents),
        patents=patents,
        analysis=analysis
    )


@router.post("/quick-check")
async def quick_prior_art_check(
    invention: str = Field(..., min_length=20),
    session: AsyncSession = Depends(get_session)
):
    """
    Quick prior art check - returns just the top 5 most similar claims.
    Faster than full search, good for initial screening.
    """
    embedding = await embedding_service.embed_text(invention)
    
    sql = text("""
        SELECT 
            p.patent_number,
            p.title,
            c.claim_number,
            c.claim_text,
            c.is_independent,
            1 - (c.embedding <=> :embedding) as similarity
        FROM claims c
        JOIN patents p ON c.patent_id = p.id
        WHERE c.embedding IS NOT NULL
        ORDER BY c.embedding <=> :embedding
        LIMIT 5
    """)
    
    result = await session.execute(sql, {"embedding": str(embedding)})
    rows = result.fetchall()
    
    return {
        "top_matches": [
            {
                "patent_number": row[0],
                "patent_title": row[1],
                "claim_number": row[2],
                "claim_text": row[3][:300] + "..." if len(row[3]) > 300 else row[3],
                "is_independent": row[4],
                "similarity": round(float(row[5]) * 100, 1) if row[5] else 0
            }
            for row in rows
        ]
    }


@router.post("/compare-to-claims")
async def compare_invention_to_claims(
    invention: str = Field(..., min_length=20),
    patent_id: str = Field(...),
    session: AsyncSession = Depends(get_session)
):
    """
    Compare your invention description against all claims of a specific patent.
    Use after prior art search to deep-dive into a particular patent.
    """
    # Get invention embedding
    invention_embedding = await embedding_service.embed_text(invention)
    
    # Get patent
    patent_result = await session.execute(
        select(Patent).where(Patent.id == patent_id)
    )
    patent = patent_result.scalar_one_or_none()
    
    if not patent:
        raise HTTPException(status_code=404, detail="Patent not found")
    
    # Get all claims for this patent
    claims_result = await session.execute(
        select(Claim)
        .where(Claim.patent_id == patent_id)
        .order_by(Claim.claim_number)
    )
    claims = claims_result.scalars().all()
    
    if not claims:
        raise HTTPException(status_code=404, detail="No claims found for this patent")
    
    # Calculate similarity for each claim
    claim_comparisons = []
    for claim in claims:
        if claim.embedding:
            similarity = embedding_service.cosine_similarity(
                invention_embedding,
                list(claim.embedding)
            )
        else:
            similarity = 0.0
        
        if similarity >= 0.75:
            risk = "high"
        elif similarity >= 0.55:
            risk = "medium"
        else:
            risk = "low"
        
        claim_comparisons.append({
            "claim_number": claim.claim_number,
            "claim_text": claim.claim_text,
            "is_independent": claim.is_independent,
            "parent_claim": claim.parent_claim_number,
            "claim_type": claim.claim_type,
            "similarity": round(similarity * 100, 1),
            "risk_level": risk
        })
    
    # Sort by similarity
    claim_comparisons.sort(key=lambda c: c["similarity"], reverse=True)
    
    return {
        "patent": {
            "id": patent.id,
            "patent_number": patent.patent_number,
            "title": patent.title,
            "abstract": patent.abstract,
            "applicant": patent.applicant
        },
        "total_claims": len(claims),
        "high_risk_claims": len([c for c in claim_comparisons if c["risk_level"] == "high"]),
        "claim_comparisons": claim_comparisons
    }


async def _analyze_prior_art(
    invention: str,
    blocking_patents: List[BlockingPatent]
) -> PriorArtAnalysis:
    """Use LLM to analyze prior art risk and provide recommendations."""
    
    # Build context
    patents_context = "\n\n".join([
        f"PATENT: {p.patent_number or 'Unknown'} - {p.title}\n"
        f"Highest similarity: {p.highest_similarity:.1%}\n"
        f"Top blocking claim (Claim {p.blocking_claims[0].claim_number}): "
        f"{p.blocking_claims[0].claim_text[:400]}..."
        for p in blocking_patents[:5]
    ])
    
    prompt = f"""You are a patent attorney AI. Analyze the freedom to operate for this invention.

INVENTION DESCRIPTION:
{invention[:1500]}

POTENTIALLY BLOCKING PRIOR ART:
{patents_context}

Analyze and respond in JSON format:
{{
    "freedom_to_operate": "likely|uncertain|unlikely",
    "key_risks": ["risk 1", "risk 2", ...],
    "design_around_suggestions": ["suggestion 1", "suggestion 2", ...],
    "recommendation": "Brief recommendation for next steps"
}}

Consider:
1. How similar are the blocking claims to the invention?
2. Are there clear differences that could avoid infringement?
3. What modifications could help design around the prior art?

Be practical and specific."""

    from openai import AsyncOpenAI
    from app.core.config import settings
    import json
    
    client = AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url
    )
    
    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content
        
        # Parse JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        result = json.loads(content.strip())
        
        return PriorArtAnalysis(
            freedom_to_operate=result.get("freedom_to_operate", "uncertain"),
            key_risks=result.get("key_risks", []),
            design_around_suggestions=result.get("design_around_suggestions", []),
            recommendation=result.get("recommendation", "")
        )
        
    except Exception as e:
        return PriorArtAnalysis(
            freedom_to_operate="uncertain",
            key_risks=["Analysis unavailable - manual review recommended"],
            design_around_suggestions=[],
            recommendation=f"LLM analysis failed: {str(e)}"
        )
