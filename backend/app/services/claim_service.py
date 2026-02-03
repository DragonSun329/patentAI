"""Claim service - manage claims and perform claim-level comparisons."""
import uuid
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.patent import Patent, Claim, ClaimComparison, ComparisonResult
from app.services.claim_parser import claim_parser, ParsedClaim
from app.services.embedding import embedding_service
from app.services.llm import llm_service


@dataclass
class ClaimMatch:
    """A matching pair of claims with similarity info."""
    source_claim: Dict[str, Any]
    target_claim: Dict[str, Any]
    similarity: float
    risk_level: str = "unknown"
    overlap_assessment: Optional[str] = None


@dataclass
class ClaimAnalysisResult:
    """Full claim-level analysis between two patents."""
    source_patent_id: str
    target_patent_id: str
    source_claims_count: int
    target_claims_count: int
    
    # Top matching claims
    top_matches: List[ClaimMatch]
    
    # Overall assessment
    highest_similarity: float
    average_similarity: float
    independent_claims_at_risk: int
    overall_risk: str
    
    # LLM summary
    summary: str
    recommendation: str


class ClaimService:
    """Service for claim-level patent analysis."""
    
    def __init__(self):
        self.similarity_threshold = 0.5  # Min similarity to consider a match
        self.high_risk_threshold = 0.8
        self.medium_risk_threshold = 0.6
    
    async def process_patent_claims(
        self,
        session: AsyncSession,
        patent_id: str
    ) -> List[Claim]:
        """
        Parse and embed claims for a patent.
        Call this when a patent is created/updated.
        """
        # Get the patent
        result = await session.execute(
            select(Patent).where(Patent.id == patent_id)
        )
        patent = result.scalar_one_or_none()
        
        if not patent or not patent.claims:
            return []
        
        # Delete existing claims
        await session.execute(
            text("DELETE FROM claims WHERE patent_id = :patent_id"),
            {"patent_id": patent_id}
        )
        
        # Parse claims
        parsed_claims = claim_parser.parse_claims(patent.claims)
        
        if not parsed_claims:
            return []
        
        # Create claim objects and embed them
        claim_objects = []
        for parsed in parsed_claims:
            claim_id = str(uuid.uuid4())
            
            # Generate embedding for this claim (with chunking for long claims)
            embedding = await embedding_service.embed_claim(
                parsed.claim_text, 
                claim_number=parsed.claim_number
            )
            
            # Extract key elements
            key_elements = claim_parser.extract_key_elements(parsed.claim_text)
            
            claim = Claim(
                id=claim_id,
                patent_id=patent_id,
                claim_number=parsed.claim_number,
                claim_text=parsed.claim_text,
                is_independent=parsed.is_independent,
                parent_claim_number=parsed.parent_claim_number,
                claim_type=parsed.claim_type,
                embedding=embedding,
                key_elements=json.dumps(key_elements) if key_elements else None
            )
            session.add(claim)
            claim_objects.append(claim)
        
        return claim_objects
    
    async def get_patent_claims(
        self,
        session: AsyncSession,
        patent_id: str
    ) -> List[Claim]:
        """Get all claims for a patent."""
        result = await session.execute(
            select(Claim)
            .where(Claim.patent_id == patent_id)
            .order_by(Claim.claim_number)
        )
        return result.scalars().all()
    
    async def compare_claims(
        self,
        session: AsyncSession,
        source_patent_id: str,
        target_patent_id: str,
        include_llm_analysis: bool = True
    ) -> ClaimAnalysisResult:
        """
        Perform claim-level comparison between two patents.
        """
        # Get claims for both patents
        source_claims = await self.get_patent_claims(session, source_patent_id)
        target_claims = await self.get_patent_claims(session, target_patent_id)
        
        # If no claims exist, try to process them
        if not source_claims:
            source_claims = await self.process_patent_claims(session, source_patent_id)
        if not target_claims:
            target_claims = await self.process_patent_claims(session, target_patent_id)
        
        if not source_claims or not target_claims:
            return ClaimAnalysisResult(
                source_patent_id=source_patent_id,
                target_patent_id=target_patent_id,
                source_claims_count=len(source_claims),
                target_claims_count=len(target_claims),
                top_matches=[],
                highest_similarity=0.0,
                average_similarity=0.0,
                independent_claims_at_risk=0,
                overall_risk="unknown",
                summary="Could not parse claims from one or both patents.",
                recommendation="Manual review required - claims could not be automatically parsed."
            )
        
        # Calculate similarities between all claim pairs
        all_matches = []
        for source_claim in source_claims:
            for target_claim in target_claims:
                if source_claim.embedding and target_claim.embedding:
                    similarity = embedding_service.cosine_similarity(
                        list(source_claim.embedding),
                        list(target_claim.embedding)
                    )
                    
                    if similarity >= self.similarity_threshold:
                        risk = self._calculate_risk_level(similarity)
                        all_matches.append(ClaimMatch(
                            source_claim=self._claim_to_dict(source_claim),
                            target_claim=self._claim_to_dict(target_claim),
                            similarity=similarity,
                            risk_level=risk
                        ))
        
        # Sort by similarity and get top matches
        all_matches.sort(key=lambda m: m.similarity, reverse=True)
        top_matches = all_matches[:10]  # Top 10 matches
        
        # Calculate statistics
        similarities = [m.similarity for m in all_matches] if all_matches else [0.0]
        highest_sim = max(similarities)
        avg_sim = sum(similarities) / len(similarities)
        
        # Count independent claims at risk
        independent_at_risk = len(set(
            m.source_claim['claim_number']
            for m in all_matches
            if m.source_claim.get('is_independent') and m.similarity >= self.medium_risk_threshold
        ))
        
        # Determine overall risk
        if highest_sim >= self.high_risk_threshold:
            overall_risk = "high"
        elif highest_sim >= self.medium_risk_threshold:
            overall_risk = "medium"
        else:
            overall_risk = "low"
        
        # LLM analysis for top matches
        summary = ""
        recommendation = ""
        
        if include_llm_analysis and top_matches:
            llm_result = await self._llm_analyze_claim_matches(
                source_claims, target_claims, top_matches[:5]
            )
            summary = llm_result.get("summary", "")
            recommendation = llm_result.get("recommendation", "")
            
            # Update top matches with LLM assessments if available
            for i, assessment in enumerate(llm_result.get("match_assessments", [])):
                if i < len(top_matches):
                    top_matches[i].overlap_assessment = assessment
        
        return ClaimAnalysisResult(
            source_patent_id=source_patent_id,
            target_patent_id=target_patent_id,
            source_claims_count=len(source_claims),
            target_claims_count=len(target_claims),
            top_matches=top_matches,
            highest_similarity=highest_sim,
            average_similarity=avg_sim,
            independent_claims_at_risk=independent_at_risk,
            overall_risk=overall_risk,
            summary=summary,
            recommendation=recommendation
        )
    
    async def find_similar_claims(
        self,
        session: AsyncSession,
        claim_text: str,
        limit: int = 10,
        exclude_patent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find claims similar to given text across all patents.
        Useful for prior art search at the claim level.
        """
        # Generate embedding for the query
        query_embedding = await embedding_service.embed_text(claim_text)
        
        # Vector search on claims table
        sql = text("""
            SELECT 
                c.id, c.patent_id, c.claim_number, c.claim_text,
                c.is_independent, c.claim_type,
                p.title as patent_title, p.patent_number,
                1 - (c.embedding <=> :embedding) as similarity
            FROM claims c
            JOIN patents p ON c.patent_id = p.id
            WHERE c.embedding IS NOT NULL
            """ + ("AND c.patent_id != :exclude_id" if exclude_patent_id else "") + """
            ORDER BY c.embedding <=> :embedding
            LIMIT :limit
        """)
        
        params = {"embedding": str(query_embedding), "limit": limit}
        if exclude_patent_id:
            params["exclude_id"] = exclude_patent_id
        
        result = await session.execute(sql, params)
        rows = result.fetchall()
        
        return [
            {
                "claim_id": row[0],
                "patent_id": row[1],
                "claim_number": row[2],
                "claim_text": row[3],
                "is_independent": row[4],
                "claim_type": row[5],
                "patent_title": row[6],
                "patent_number": row[7],
                "similarity": float(row[8]) if row[8] else 0.0
            }
            for row in rows
        ]
    
    def _claim_to_dict(self, claim: Claim) -> Dict[str, Any]:
        """Convert Claim object to dictionary."""
        return {
            "id": claim.id,
            "claim_number": claim.claim_number,
            "claim_text": claim.claim_text,
            "is_independent": claim.is_independent,
            "parent_claim_number": claim.parent_claim_number,
            "claim_type": claim.claim_type,
            "key_elements": json.loads(claim.key_elements) if claim.key_elements else []
        }
    
    def _calculate_risk_level(self, similarity: float) -> str:
        """Determine risk level from similarity score."""
        if similarity >= self.high_risk_threshold:
            return "high"
        elif similarity >= self.medium_risk_threshold:
            return "medium"
        return "low"
    
    async def _llm_analyze_claim_matches(
        self,
        source_claims: List[Claim],
        target_claims: List[Claim],
        top_matches: List[ClaimMatch]
    ) -> Dict[str, Any]:
        """Use LLM to analyze the top claim matches."""
        
        # Build context for LLM
        matches_context = "\n\n".join([
            f"MATCH {i+1} (Similarity: {m.similarity:.1%}):\n"
            f"Source Claim {m.source_claim['claim_number']} ({'Independent' if m.source_claim.get('is_independent') else 'Dependent'}):\n"
            f"{m.source_claim['claim_text'][:500]}...\n\n"
            f"Target Claim {m.target_claim['claim_number']} ({'Independent' if m.target_claim.get('is_independent') else 'Dependent'}):\n"
            f"{m.target_claim['claim_text'][:500]}..."
            for i, m in enumerate(top_matches[:5])
        ])
        
        prompt = f"""You are a patent attorney AI. Analyze these matching patent claims for potential infringement.

{matches_context}

Provide analysis in JSON format:
{{
    "summary": "Brief overall assessment of infringement risk (2-3 sentences)",
    "recommendation": "Specific action recommended",
    "match_assessments": [
        "Brief assessment for match 1",
        "Brief assessment for match 2",
        ...
    ]
}}

Focus on:
1. Whether the claims cover the same technical subject matter
2. Whether one claim would literally or equivalently infringe the other
3. Key differences that might avoid infringement

Be precise and technical."""

        from openai import AsyncOpenAI
        from app.core.config import settings
        
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
            
            return json.loads(content.strip())
        except Exception as e:
            return {
                "summary": "LLM analysis unavailable.",
                "recommendation": "Manual review recommended.",
                "match_assessments": []
            }


# Singleton instance
claim_service = ClaimService()
