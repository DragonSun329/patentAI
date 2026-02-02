"""Embedding service using Ollama."""
import asyncio
from typing import List
import httpx
import numpy as np

from app.core.config import settings


class EmbeddingService:
    """Generate embeddings using Ollama's nomic-embed-text model."""
    
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.embed_model
        self.dimensions = settings.embed_dimensions
        
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text}
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]
    
    async def embed_texts(self, texts: List[str], batch_size: int = 10) -> List[List[float]]:
        """Generate embeddings for multiple texts with batching."""
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            # Process batch concurrently
            tasks = [self.embed_text(text) for text in batch]
            batch_embeddings = await asyncio.gather(*tasks)
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a = np.array(vec1)
        b = np.array(vec2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    
    async def embed_patent(self, title: str, abstract: str, claims: str = None) -> List[float]:
        """Generate combined embedding for a patent document."""
        # Combine relevant fields with weights
        text_parts = [
            f"Title: {title}",
            f"Abstract: {abstract}",
        ]
        if claims:
            # Truncate claims to avoid token limits
            text_parts.append(f"Claims: {claims[:2000]}")
        
        combined_text = "\n\n".join(text_parts)
        return await self.embed_text(combined_text)


# Singleton instance
embedding_service = EmbeddingService()
