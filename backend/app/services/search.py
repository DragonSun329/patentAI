"""Patent search service with hybrid search capabilities."""
import json
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from rapidfuzz import fuzz, process

from app.models.patent import Patent, SearchHistory
from app.services.embedding import embedding_service
from app.core.config import settings


@dataclass
class SearchResult:
    """Search result with scores."""
    patent: Dict[str, Any]
    vector_score: float = 0.0
    fuzzy_score: float = 0.0
    combined_score: float = 0.0
    match_type: str = "hybrid"


class PatentSearchService:
    """Hybrid patent search combining vector and fuzzy matching."""
    
    def __init__(self):
        self.similarity_threshold = settings.similarity_threshold
        self.fuzzy_threshold = settings.fuzzy_threshold
        self.max_results = settings.max_results
    
    async def vector_search(
        self,
        session: AsyncSession,
        query_embedding: List[float],
        limit: int = 20
    ) -> List[tuple]:
        """Search patents by vector similarity using pgvector."""
        # Use cosine distance operator <=>
        sql = text("""
            SELECT 
                id, title, abstract, claims, patent_number, 
                applicant, classification, filing_date,
                1 - (embedding <=> :embedding) as similarity
            FROM patents
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> :embedding
            LIMIT :limit
        """)
        
        result = await session.execute(
            sql,
            {"embedding": str(query_embedding), "limit": limit}
        )
        return result.fetchall()
    
    async def fuzzy_search(
        self,
        session: AsyncSession,
        query: str,
        limit: int = 20
    ) -> List[tuple]:
        """Search patents by fuzzy text matching."""
        # Get all patents for fuzzy matching
        # In production, use pg_trgm extension for DB-side fuzzy search
        result = await session.execute(
            select(Patent).limit(1000)  # Limit for performance
        )
        patents = result.scalars().all()
        
        # Build search corpus
        corpus = []
        patent_map = {}
        for p in patents:
            # Combine searchable text
            search_text = f"{p.title} {p.abstract}"
            corpus.append(search_text)
            patent_map[search_text] = p
        
        # Fuzzy match
        matches = process.extract(
            query,
            corpus,
            scorer=fuzz.token_set_ratio,
            limit=limit
        )
        
        results = []
        for match_text, score, _ in matches:
            if score >= self.fuzzy_threshold:
                patent = patent_map[match_text]
                results.append((patent, score / 100.0))
        
        return results
    
    async def hybrid_search(
        self,
        session: AsyncSession,
        query: str,
        limit: int = None,
        vector_weight: float = 0.7,
        fuzzy_weight: float = 0.3
    ) -> List[SearchResult]:
        """
        Hybrid search combining vector and fuzzy matching.
        
        Args:
            query: Search query text
            limit: Maximum results
            vector_weight: Weight for vector similarity (0-1)
            fuzzy_weight: Weight for fuzzy matching (0-1)
        """
        start_time = time.time()
        limit = limit or self.max_results
        
        # Get query embedding
        query_embedding = await embedding_service.embed_text(query)
        
        # Run both searches
        vector_results = await self.vector_search(session, query_embedding, limit * 2)
        fuzzy_results = await self.fuzzy_search(session, query, limit * 2)
        
        # Combine results
        combined = {}
        
        # Add vector results
        for row in vector_results:
            patent_id = row[0]
            combined[patent_id] = SearchResult(
                patent={
                    "id": row[0],
                    "title": row[1],
                    "abstract": row[2],
                    "claims": row[3],
                    "patent_number": row[4],
                    "applicant": row[5],
                    "classification": row[6],
                    "filing_date": str(row[7]) if row[7] else None,
                },
                vector_score=float(row[8]) if row[8] else 0.0,
                match_type="vector"
            )
        
        # Merge fuzzy results
        for patent, score in fuzzy_results:
            patent_id = patent.id
            if patent_id in combined:
                combined[patent_id].fuzzy_score = score
                combined[patent_id].match_type = "hybrid"
            else:
                combined[patent_id] = SearchResult(
                    patent={
                        "id": patent.id,
                        "title": patent.title,
                        "abstract": patent.abstract,
                        "claims": patent.claims,
                        "patent_number": patent.patent_number,
                        "applicant": patent.applicant,
                        "classification": patent.classification,
                        "filing_date": str(patent.filing_date) if patent.filing_date else None,
                    },
                    fuzzy_score=score,
                    match_type="fuzzy"
                )
        
        # Calculate combined scores
        for result in combined.values():
            result.combined_score = (
                result.vector_score * vector_weight +
                result.fuzzy_score * fuzzy_weight
            )
        
        # Sort by combined score and limit
        results = sorted(
            combined.values(),
            key=lambda x: x.combined_score,
            reverse=True
        )[:limit]
        
        # Filter by threshold
        results = [r for r in results if r.combined_score >= self.similarity_threshold]
        
        # Log search history
        latency_ms = (time.time() - start_time) * 1000
        history = SearchHistory(
            query_text=query,
            query_type="hybrid",
            results_count=len(results),
            top_score=results[0].combined_score if results else None,
            latency_ms=latency_ms
        )
        session.add(history)
        
        return results


# Singleton instance
search_service = PatentSearchService()
