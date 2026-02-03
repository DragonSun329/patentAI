"""Cross-encoder reranker for improving search results.

Uses a cross-encoder model to rerank top-k results from vector search.
This significantly improves precision by considering query-document interaction.
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import httpx

from app.core.config import settings


@dataclass
class RankedResult:
    """A reranked search result."""
    item: Dict[str, Any]
    original_score: float
    rerank_score: float
    final_score: float


class RerankerService:
    """
    Cross-encoder reranking service.
    
    Options:
    1. Local: sentence-transformers CrossEncoder (requires torch)
    2. API: Cohere rerank, Jina rerank, or OpenRouter
    
    We use OpenRouter with a capable model for zero-dependency setup.
    For production, consider Cohere rerank API or local cross-encoder.
    """
    
    def __init__(self):
        self.enabled = True
        self.top_k_rerank = 20  # Rerank top 20 from vector search
        self.alpha = 0.3  # Weight for original score (0.3 original + 0.7 rerank)
    
    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        text_field: str = "text",
        score_field: str = "score",
        top_k: int = 10
    ) -> List[RankedResult]:
        """
        Rerank search results using cross-encoder scoring.
        
        Args:
            query: The search query
            results: List of search results with text and score
            text_field: Field name containing the text to compare
            score_field: Field name containing the original score
            top_k: Number of results to return after reranking
        
        Returns:
            Reranked results with combined scores
        """
        if not results or not self.enabled:
            return [
                RankedResult(
                    item=r,
                    original_score=r.get(score_field, 0),
                    rerank_score=r.get(score_field, 0),
                    final_score=r.get(score_field, 0)
                )
                for r in results[:top_k]
            ]
        
        # Only rerank top candidates
        candidates = results[:self.top_k_rerank]
        
        # Score each candidate
        scored = []
        for result in candidates:
            text = self._extract_text(result, text_field)
            original_score = result.get(score_field, 0)
            
            if not text:
                rerank_score = original_score
            else:
                rerank_score = await self._score_pair(query, text)
            
            # Combine scores
            final_score = (self.alpha * original_score) + ((1 - self.alpha) * rerank_score)
            
            scored.append(RankedResult(
                item=result,
                original_score=original_score,
                rerank_score=rerank_score,
                final_score=final_score
            ))
        
        # Sort by final score
        scored.sort(key=lambda x: x.final_score, reverse=True)
        
        return scored[:top_k]
    
    async def rerank_batch(
        self,
        query: str,
        results: List[Dict[str, Any]],
        text_field: str = "text",
        score_field: str = "score"
    ) -> List[RankedResult]:
        """Batch rerank using LLM for efficiency."""
        if not results or not self.enabled:
            return [
                RankedResult(item=r, original_score=r.get(score_field, 0),
                           rerank_score=0, final_score=r.get(score_field, 0))
                for r in results
            ]
        
        candidates = results[:self.top_k_rerank]
        
        # Build batch scoring prompt
        texts = [self._extract_text(r, text_field) for r in candidates]
        scores = await self._batch_score(query, texts)
        
        scored = []
        for i, result in enumerate(candidates):
            original_score = result.get(score_field, 0)
            rerank_score = scores[i] if i < len(scores) else 0
            final_score = (self.alpha * original_score) + ((1 - self.alpha) * rerank_score)
            
            scored.append(RankedResult(
                item=result,
                original_score=original_score,
                rerank_score=rerank_score,
                final_score=final_score
            ))
        
        scored.sort(key=lambda x: x.final_score, reverse=True)
        return scored
    
    def _extract_text(self, result: Dict[str, Any], text_field: str) -> str:
        """Extract text from result, handling nested fields."""
        if text_field in result:
            return str(result[text_field])
        
        # Try common patent fields
        parts = []
        for field in ["title", "abstract", "claim_text", "claims"]:
            if field in result and result[field]:
                parts.append(str(result[field])[:500])
        
        return " ".join(parts) if parts else ""
    
    async def _score_pair(self, query: str, document: str) -> float:
        """
        Score a query-document pair.
        
        Uses LLM to estimate relevance (0-1).
        For production, use dedicated reranker like Cohere or local cross-encoder.
        """
        # Truncate for efficiency
        doc_truncated = document[:1000] if len(document) > 1000 else document
        
        prompt = f"""Rate the relevance of this document to the query on a scale of 0.0 to 1.0.
Only respond with a single decimal number.

Query: {query}

Document: {doc_truncated}

Relevance score (0.0-1.0):"""

        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url
            )
            
            response = await client.chat.completions.create(
                model="openai/gpt-4o-mini",  # Fast and cheap for scoring
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10
            )
            
            score_text = response.choices[0].message.content.strip()
            # Extract number
            import re
            match = re.search(r'(\d+\.?\d*)', score_text)
            if match:
                score = float(match.group(1))
                return min(1.0, max(0.0, score))
            return 0.5
            
        except Exception as e:
            # Fallback to original score behavior
            return 0.5
    
    async def _batch_score(self, query: str, documents: List[str]) -> List[float]:
        """Score multiple documents in one LLM call."""
        if not documents:
            return []
        
        # Build numbered list
        doc_list = "\n\n".join([
            f"[{i+1}] {doc[:400]}..." if len(doc) > 400 else f"[{i+1}] {doc}"
            for i, doc in enumerate(documents)
        ])
        
        prompt = f"""Rate each document's relevance to the query (0.0-1.0).
Respond with ONLY comma-separated scores in order, nothing else.

Query: {query}

Documents:
{doc_list}

Scores (comma-separated):"""

        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url
            )
            
            response = await client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=100
            )
            
            score_text = response.choices[0].message.content.strip()
            
            # Parse comma-separated scores
            import re
            numbers = re.findall(r'(\d+\.?\d*)', score_text)
            scores = [min(1.0, max(0.0, float(n))) for n in numbers]
            
            # Pad if needed
            while len(scores) < len(documents):
                scores.append(0.5)
            
            return scores[:len(documents)]
            
        except Exception as e:
            return [0.5] * len(documents)


# Singleton
reranker_service = RerankerService()
