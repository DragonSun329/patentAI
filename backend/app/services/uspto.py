"""USPTO Open Data API integration for patent ingestion."""
import asyncio
import uuid
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from dataclasses import dataclass
import httpx

from app.core.config import settings


@dataclass
class USPTOPatent:
    """Patent data from USPTO."""
    patent_number: str
    title: str
    abstract: str
    claims: Optional[str]
    description: Optional[str]
    applicant: Optional[str]
    inventors: Optional[str]
    filing_date: Optional[date]
    publication_date: Optional[date]
    classification: Optional[str]  # CPC/IPC code


class USPTOService:
    """
    Service for fetching patent data from USPTO Open Data Portal.
    
    Uses the PatentsView API (free, no key required):
    https://patentsview.org/apis/api-endpoints/patents
    """
    
    BASE_URL = "https://api.patentsview.org/patents/query"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def search_patents(
        self,
        query: str,
        start_date: Optional[str] = None,  # YYYY-MM-DD
        end_date: Optional[str] = None,
        cpc_code: Optional[str] = None,
        limit: int = 25,
        page: int = 1
    ) -> List[USPTOPatent]:
        """
        Search USPTO patents by keyword and filters.
        
        Args:
            query: Search text (searches title and abstract)
            start_date: Filter by grant date start
            end_date: Filter by grant date end
            cpc_code: Filter by CPC classification
            limit: Results per page (max 100)
            page: Page number
        
        Returns:
            List of USPTOPatent objects
        """
        # Build query conditions
        conditions = []
        
        # Text search on title and abstract
        if query:
            conditions.append({
                "_or": [
                    {"_text_any": {"patent_title": query}},
                    {"_text_any": {"patent_abstract": query}}
                ]
            })
        
        # Date filters
        if start_date:
            conditions.append({"_gte": {"patent_date": start_date}})
        if end_date:
            conditions.append({"_lte": {"patent_date": end_date}})
        
        # CPC classification filter
        if cpc_code:
            conditions.append({"_begins": {"cpc_group_id": cpc_code}})
        
        # Combine conditions
        if len(conditions) > 1:
            query_filter = {"_and": conditions}
        elif conditions:
            query_filter = conditions[0]
        else:
            # Default: recent patents
            query_filter = {"_gte": {"patent_date": "2020-01-01"}}
        
        # Fields to retrieve
        fields = [
            "patent_number",
            "patent_title",
            "patent_abstract",
            "patent_date",
            "patent_firstnamed_assignee_organization",
            "patent_firstnamed_inventor_name",
        ]
        
        # API request body
        request_body = {
            "q": query_filter,
            "f": fields,
            "o": {
                "page": page,
                "per_page": min(limit, 100)
            },
            "s": [{"patent_date": "desc"}]
        }
        
        try:
            response = await self.client.post(
                self.BASE_URL,
                json=request_body,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            
            patents = []
            for p in data.get("patents", []):
                patents.append(USPTOPatent(
                    patent_number=p.get("patent_number"),
                    title=p.get("patent_title", ""),
                    abstract=p.get("patent_abstract", ""),
                    claims=None,  # Not available in search results
                    description=None,
                    applicant=p.get("patent_firstnamed_assignee_organization"),
                    inventors=p.get("patent_firstnamed_inventor_name"),
                    filing_date=None,
                    publication_date=self._parse_date(p.get("patent_date")),
                    classification=None
                ))
            
            return patents
            
        except httpx.HTTPError as e:
            print(f"USPTO API error: {e}")
            return []
    
    async def get_patent_details(self, patent_number: str) -> Optional[USPTOPatent]:
        """
        Get full patent details including claims.
        
        Uses PatentsView API with expanded fields.
        """
        # Clean patent number
        patent_number = re.sub(r'[^0-9]', '', patent_number)
        
        request_body = {
            "q": {"patent_number": patent_number},
            "f": [
                "patent_number",
                "patent_title",
                "patent_abstract",
                "patent_date",
                "patent_firstnamed_assignee_organization",
                "patent_firstnamed_inventor_name",
                "cpc_group_id",
                "claims"
            ],
            "o": {"include_subentity_total_counts": True}
        }
        
        try:
            response = await self.client.post(
                self.BASE_URL,
                json=request_body,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            
            patents = data.get("patents", [])
            if not patents:
                return None
            
            p = patents[0]
            
            # Extract claims text if available
            claims_text = None
            claims_data = p.get("claims", [])
            if claims_data:
                claims_text = "\n".join([
                    f"{c.get('claim_number', i+1)}. {c.get('claim_text', '')}"
                    for i, c in enumerate(claims_data)
                ])
            
            # Get first CPC code
            cpc = None
            if p.get("cpc_group_id"):
                cpc = p.get("cpc_group_id")
            
            return USPTOPatent(
                patent_number=p.get("patent_number"),
                title=p.get("patent_title", ""),
                abstract=p.get("patent_abstract", ""),
                claims=claims_text,
                description=None,  # Full description not available via this API
                applicant=p.get("patent_firstnamed_assignee_organization"),
                inventors=p.get("patent_firstnamed_inventor_name"),
                filing_date=None,
                publication_date=self._parse_date(p.get("patent_date")),
                classification=cpc
            )
            
        except httpx.HTTPError as e:
            print(f"USPTO API error: {e}")
            return None
    
    async def get_patents_by_assignee(
        self,
        assignee: str,
        limit: int = 25
    ) -> List[USPTOPatent]:
        """Get patents by assignee/company name."""
        request_body = {
            "q": {"_text_any": {"assignee_organization": assignee}},
            "f": [
                "patent_number",
                "patent_title",
                "patent_abstract",
                "patent_date",
                "patent_firstnamed_assignee_organization",
                "patent_firstnamed_inventor_name",
            ],
            "o": {"per_page": min(limit, 100)},
            "s": [{"patent_date": "desc"}]
        }
        
        try:
            response = await self.client.post(
                self.BASE_URL,
                json=request_body,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                USPTOPatent(
                    patent_number=p.get("patent_number"),
                    title=p.get("patent_title", ""),
                    abstract=p.get("patent_abstract", ""),
                    claims=None,
                    description=None,
                    applicant=p.get("patent_firstnamed_assignee_organization"),
                    inventors=p.get("patent_firstnamed_inventor_name"),
                    filing_date=None,
                    publication_date=self._parse_date(p.get("patent_date")),
                    classification=None
                )
                for p in data.get("patents", [])
            ]
            
        except httpx.HTTPError as e:
            print(f"USPTO API error: {e}")
            return []
    
    async def get_patents_by_cpc(
        self,
        cpc_code: str,
        start_date: Optional[str] = None,
        limit: int = 25
    ) -> List[USPTOPatent]:
        """
        Get patents by CPC classification code.
        
        CPC codes: https://www.uspto.gov/web/patents/classification/cpc/html/cpc.html
        Examples:
            - G06F: Computing
            - H04L: Network protocols
            - G06N: AI/ML
        """
        conditions = [{"_begins": {"cpc_group_id": cpc_code}}]
        
        if start_date:
            conditions.append({"_gte": {"patent_date": start_date}})
        
        request_body = {
            "q": {"_and": conditions} if len(conditions) > 1 else conditions[0],
            "f": [
                "patent_number",
                "patent_title",
                "patent_abstract",
                "patent_date",
                "patent_firstnamed_assignee_organization",
                "cpc_group_id",
            ],
            "o": {"per_page": min(limit, 100)},
            "s": [{"patent_date": "desc"}]
        }
        
        try:
            response = await self.client.post(
                self.BASE_URL,
                json=request_body,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                USPTOPatent(
                    patent_number=p.get("patent_number"),
                    title=p.get("patent_title", ""),
                    abstract=p.get("patent_abstract", ""),
                    claims=None,
                    description=None,
                    applicant=p.get("patent_firstnamed_assignee_organization"),
                    inventors=None,
                    filing_date=None,
                    publication_date=self._parse_date(p.get("patent_date")),
                    classification=p.get("cpc_group_id")
                )
                for p in data.get("patents", [])
            ]
            
        except httpx.HTTPError as e:
            print(f"USPTO API error: {e}")
            return []
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse USPTO date string to date object."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
uspto_service = USPTOService()
