"""LLM service for patent analysis and explanation."""
import json
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI

from app.core.config import settings


class LLMService:
    """LLM-powered patent analysis using OpenRouter."""
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url
        )
        self.model = settings.llm_model
    
    async def analyze_infringement(
        self,
        source_patent: Dict[str, Any],
        target_patent: Dict[str, Any],
        similarity_score: float
    ) -> Dict[str, Any]:
        """
        Analyze potential patent infringement between two patents.
        
        Returns:
            Dict with risk level, explanation, and key overlaps
        """
        prompt = f"""You are a patent attorney AI assistant. Analyze the following two patents for potential infringement.

SOURCE PATENT:
Title: {source_patent.get('title', 'N/A')}
Abstract: {source_patent.get('abstract', 'N/A')}
Claims: {source_patent.get('claims', 'N/A')[:2000] if source_patent.get('claims') else 'N/A'}

TARGET PATENT (potentially infringing):
Title: {target_patent.get('title', 'N/A')}
Abstract: {target_patent.get('abstract', 'N/A')}
Claims: {target_patent.get('claims', 'N/A')[:2000] if target_patent.get('claims') else 'N/A'}

Similarity Score: {similarity_score:.2%}

Analyze and respond in JSON format:
{{
    "risk_level": "low|medium|high",
    "confidence": 0.0-1.0,
    "key_overlaps": ["overlap 1", "overlap 2", ...],
    "differences": ["difference 1", "difference 2", ...],
    "explanation": "Brief explanation of the analysis",
    "recommendation": "What action to take"
}}

Be precise and technical. Focus on claim overlap and technical similarities."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content
        
        # Parse JSON from response
        try:
            # Try to extract JSON from the response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content.strip())
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            result = {
                "risk_level": "medium" if similarity_score > 0.7 else "low",
                "confidence": similarity_score,
                "key_overlaps": [],
                "differences": [],
                "explanation": content[:500],
                "recommendation": "Manual review recommended"
            }
        
        return result
    
    async def summarize_patent(self, patent: Dict[str, Any]) -> str:
        """Generate a concise summary of a patent."""
        prompt = f"""Summarize this patent in 2-3 sentences, focusing on the key innovation:

Title: {patent.get('title', 'N/A')}
Abstract: {patent.get('abstract', 'N/A')}

Be technical but concise."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200
        )
        
        return response.choices[0].message.content
    
    async def extract_key_claims(self, claims_text: str) -> List[str]:
        """Extract and simplify key claims from patent claims text."""
        if not claims_text:
            return []
        
        prompt = f"""Extract the 3-5 most important claims from this patent claims text.
Return as a JSON array of simplified claim statements.

Claims:
{claims_text[:3000]}

Response format: ["claim 1", "claim 2", ...]"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500
        )
        
        content = response.choices[0].message.content
        
        try:
            if "```" in content:
                content = content.split("```")[1].split("```")[0]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content.strip())
        except json.JSONDecodeError:
            return []


# Singleton instance
llm_service = LLMService()
