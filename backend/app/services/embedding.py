"""Embedding service using Ollama with caching and chunking."""
import asyncio
import hashlib
from typing import List, Optional
import httpx
import numpy as np

from app.core.config import settings


class EmbeddingService:
    """Generate embeddings using Ollama with smart caching and chunking."""
    
    # Chunk settings for long texts
    MAX_CHUNK_CHARS = 2000  # nomic-embed-text context is ~8k tokens
    CHUNK_OVERLAP = 200
    
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.embed_model
        self.dimensions = settings.embed_dimensions
        self._cache = None  # Lazy load to avoid circular import
    
    @property
    def cache(self):
        """Lazy load cache service."""
        if self._cache is None:
            from app.services.cache import cache_service
            self._cache = cache_service
        return self._cache
    
    def _hash_text(self, text: str) -> str:
        """Hash text for cache key."""
        return hashlib.sha256(text.encode()).hexdigest()[:32]
    
    async def embed_text(self, text: str, use_cache: bool = True) -> List[float]:
        """Generate embedding for a single text with caching."""
        text = text.strip()
        if not text:
            return [0.0] * self.dimensions
        
        # Check cache first
        if use_cache and self.cache.redis:
            text_hash = self._hash_text(text)
            cached = await self.cache.get_embedding(text_hash)
            if cached:
                return cached
        
        # Generate embedding
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text}
            )
            response.raise_for_status()
            data = response.json()
            embedding = data["embedding"]
        
        # Cache it
        if use_cache and self.cache.redis:
            await self.cache.set_embedding(text_hash, embedding)
        
        return embedding
    
    def chunk_text(self, text: str) -> List[str]:
        """Split long text into overlapping chunks."""
        if len(text) <= self.MAX_CHUNK_CHARS:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.MAX_CHUNK_CHARS
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end
                for sep in ['. ', '.\n', '; ', ';\n']:
                    last_sep = text[start:end].rfind(sep)
                    if last_sep > self.MAX_CHUNK_CHARS // 2:
                        end = start + last_sep + len(sep)
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.CHUNK_OVERLAP
        
        return chunks
    
    async def embed_text_chunked(self, text: str) -> List[float]:
        """Embed long text by chunking and averaging embeddings."""
        chunks = self.chunk_text(text)
        
        if len(chunks) == 1:
            return await self.embed_text(chunks[0])
        
        # Embed all chunks
        embeddings = await self.embed_texts(chunks)
        
        # Average the embeddings (weighted by chunk length could be better)
        avg_embedding = np.mean(embeddings, axis=0)
        # Normalize
        avg_embedding = avg_embedding / np.linalg.norm(avg_embedding)
        
        return avg_embedding.tolist()
    
    async def embed_texts(self, texts: List[str], batch_size: int = 5) -> List[List[float]]:
        """Generate embeddings for multiple texts with batching."""
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            tasks = [self.embed_text(text) for text in batch]
            batch_embeddings = await asyncio.gather(*tasks)
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a = np.array(vec1)
        b = np.array(vec2)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
    
    async def embed_patent(self, title: str, abstract: str, claims: str = None) -> List[float]:
        """Generate combined embedding for a patent document."""
        # Combine with field labels for better semantic understanding
        text_parts = [f"Title: {title}", f"Abstract: {abstract}"]
        
        if claims:
            # Chunk claims if too long
            if len(claims) > 3000:
                claims = claims[:3000]  # Truncate for patent-level embedding
            text_parts.append(f"Claims: {claims}")
        
        combined_text = "\n\n".join(text_parts)
        return await self.embed_text(combined_text)
    
    async def embed_claim(self, claim_text: str, claim_number: int = None) -> List[float]:
        """Generate embedding for a single claim with chunking if needed."""
        # Prefix with claim number for context
        if claim_number:
            text = f"Patent Claim {claim_number}: {claim_text}"
        else:
            text = f"Patent Claim: {claim_text}"
        
        # Use chunked embedding for long claims
        if len(text) > self.MAX_CHUNK_CHARS:
            return await self.embed_text_chunked(text)
        
        return await self.embed_text(text)


# Singleton instance
embedding_service = EmbeddingService()
