"""Patent ingestion API - USPTO import and bulk operations."""
import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.patent import Patent
from app.services.uspto import uspto_service, USPTOPatent
from app.services.embedding import embedding_service
from app.services.claim_service import claim_service


router = APIRouter(prefix="/ingest", tags=["ingest"])


# Request/Response models
class USPTOSearchRequest(BaseModel):
    """USPTO search request."""
    query: str = Field(..., min_length=1, description="Search keywords")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    cpc_code: Optional[str] = Field(None, description="CPC classification code (e.g., G06F)")
    limit: int = Field(default=25, ge=1, le=100)


class USPTOPatentPreview(BaseModel):
    """Preview of USPTO patent before import."""
    patent_number: str
    title: str
    abstract: str
    applicant: Optional[str]
    publication_date: Optional[str]
    classification: Optional[str]
    already_imported: bool = False


class USPTOSearchResponse(BaseModel):
    """USPTO search results."""
    total: int
    patents: List[USPTOPatentPreview]


class ImportRequest(BaseModel):
    """Request to import specific patents."""
    patent_numbers: List[str] = Field(..., min_items=1, max_items=50)


class ImportResult(BaseModel):
    """Result of import operation."""
    patent_number: str
    success: bool
    patent_id: Optional[str] = None
    error: Optional[str] = None


class ImportResponse(BaseModel):
    """Import operation response."""
    total: int
    imported: int
    failed: int
    results: List[ImportResult]


class BulkImportRequest(BaseModel):
    """Bulk import by search criteria."""
    query: Optional[str] = None
    cpc_code: Optional[str] = None
    assignee: Optional[str] = None
    start_date: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=100)


# Endpoints
@router.post("/uspto/search", response_model=USPTOSearchResponse)
async def search_uspto(
    request: USPTOSearchRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Search USPTO patents by keyword and filters.
    Returns previews - use /import to add to database.
    """
    patents = await uspto_service.search_patents(
        query=request.query,
        start_date=request.start_date,
        end_date=request.end_date,
        cpc_code=request.cpc_code,
        limit=request.limit
    )
    
    # Check which are already imported
    patent_numbers = [p.patent_number for p in patents]
    existing = await session.execute(
        select(Patent.patent_number).where(Patent.patent_number.in_(patent_numbers))
    )
    existing_numbers = set(r[0] for r in existing.fetchall())
    
    previews = [
        USPTOPatentPreview(
            patent_number=p.patent_number,
            title=p.title,
            abstract=p.abstract[:500] + "..." if len(p.abstract) > 500 else p.abstract,
            applicant=p.applicant,
            publication_date=str(p.publication_date) if p.publication_date else None,
            classification=p.classification,
            already_imported=p.patent_number in existing_numbers
        )
        for p in patents
    ]
    
    return USPTOSearchResponse(
        total=len(previews),
        patents=previews
    )


@router.post("/uspto/import", response_model=ImportResponse)
async def import_patents(
    request: ImportRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    """
    Import specific patents from USPTO by patent number.
    Fetches full details including claims and generates embeddings.
    """
    results = []
    imported = 0
    failed = 0
    
    for patent_number in request.patent_numbers:
        # Check if already exists
        existing = await session.execute(
            select(Patent).where(Patent.patent_number == patent_number)
        )
        if existing.scalar_one_or_none():
            results.append(ImportResult(
                patent_number=patent_number,
                success=False,
                error="Already imported"
            ))
            failed += 1
            continue
        
        # Fetch full details from USPTO
        uspto_patent = await uspto_service.get_patent_details(patent_number)
        
        if not uspto_patent:
            results.append(ImportResult(
                patent_number=patent_number,
                success=False,
                error="Not found in USPTO database"
            ))
            failed += 1
            continue
        
        try:
            # Generate embedding
            embedding = await embedding_service.embed_patent(
                uspto_patent.title,
                uspto_patent.abstract,
                uspto_patent.claims
            )
            
            # Create patent record
            patent_id = str(uuid.uuid4())
            db_patent = Patent(
                id=patent_id,
                title=uspto_patent.title,
                abstract=uspto_patent.abstract,
                claims=uspto_patent.claims,
                description=uspto_patent.description,
                patent_number=uspto_patent.patent_number,
                applicant=uspto_patent.applicant,
                inventors=uspto_patent.inventors,
                classification=uspto_patent.classification,
                filing_date=uspto_patent.filing_date,
                publication_date=uspto_patent.publication_date,
                embedding=embedding
            )
            
            session.add(db_patent)
            await session.flush()  # Get ID before processing claims
            
            # Process claims in background if available
            if uspto_patent.claims:
                await claim_service.process_patent_claims(session, patent_id)
            
            results.append(ImportResult(
                patent_number=patent_number,
                success=True,
                patent_id=patent_id
            ))
            imported += 1
            
        except Exception as e:
            results.append(ImportResult(
                patent_number=patent_number,
                success=False,
                error=str(e)
            ))
            failed += 1
    
    await session.commit()
    
    return ImportResponse(
        total=len(request.patent_numbers),
        imported=imported,
        failed=failed,
        results=results
    )


@router.post("/uspto/bulk", response_model=ImportResponse)
async def bulk_import(
    request: BulkImportRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Bulk import patents by search criteria.
    Searches USPTO and imports all matching patents.
    """
    patents: List[USPTOPatent] = []
    
    # Search based on criteria provided
    if request.assignee:
        patents = await uspto_service.get_patents_by_assignee(
            request.assignee,
            limit=request.limit
        )
    elif request.cpc_code:
        patents = await uspto_service.get_patents_by_cpc(
            request.cpc_code,
            start_date=request.start_date,
            limit=request.limit
        )
    elif request.query:
        patents = await uspto_service.search_patents(
            query=request.query,
            start_date=request.start_date,
            limit=request.limit
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide query, cpc_code, or assignee"
        )
    
    if not patents:
        return ImportResponse(total=0, imported=0, failed=0, results=[])
    
    # Import each patent
    results = []
    imported = 0
    failed = 0
    
    for uspto_patent in patents:
        # Check if already exists
        existing = await session.execute(
            select(Patent).where(Patent.patent_number == uspto_patent.patent_number)
        )
        if existing.scalar_one_or_none():
            results.append(ImportResult(
                patent_number=uspto_patent.patent_number,
                success=False,
                error="Already imported"
            ))
            failed += 1
            continue
        
        try:
            # Fetch full details (including claims) if not available
            if not uspto_patent.claims:
                full_patent = await uspto_service.get_patent_details(uspto_patent.patent_number)
                if full_patent:
                    uspto_patent = full_patent
            
            # Generate embedding
            embedding = await embedding_service.embed_patent(
                uspto_patent.title,
                uspto_patent.abstract,
                uspto_patent.claims
            )
            
            # Create patent record
            patent_id = str(uuid.uuid4())
            db_patent = Patent(
                id=patent_id,
                title=uspto_patent.title,
                abstract=uspto_patent.abstract,
                claims=uspto_patent.claims,
                description=uspto_patent.description,
                patent_number=uspto_patent.patent_number,
                applicant=uspto_patent.applicant,
                inventors=uspto_patent.inventors,
                classification=uspto_patent.classification,
                filing_date=uspto_patent.filing_date,
                publication_date=uspto_patent.publication_date,
                embedding=embedding
            )
            
            session.add(db_patent)
            await session.flush()
            
            # Process claims
            if uspto_patent.claims:
                await claim_service.process_patent_claims(session, patent_id)
            
            results.append(ImportResult(
                patent_number=uspto_patent.patent_number,
                success=True,
                patent_id=patent_id
            ))
            imported += 1
            
        except Exception as e:
            results.append(ImportResult(
                patent_number=uspto_patent.patent_number,
                success=False,
                error=str(e)
            ))
            failed += 1
    
    await session.commit()
    
    return ImportResponse(
        total=len(patents),
        imported=imported,
        failed=failed,
        results=results
    )


@router.get("/uspto/patent/{patent_number}")
async def get_uspto_patent(patent_number: str):
    """
    Preview a USPTO patent before importing.
    Returns full details including claims.
    """
    patent = await uspto_service.get_patent_details(patent_number)
    
    if not patent:
        raise HTTPException(status_code=404, detail="Patent not found")
    
    return {
        "patent_number": patent.patent_number,
        "title": patent.title,
        "abstract": patent.abstract,
        "claims": patent.claims,
        "applicant": patent.applicant,
        "inventors": patent.inventors,
        "publication_date": str(patent.publication_date) if patent.publication_date else None,
        "classification": patent.classification
    }


@router.get("/uspto/assignee/{assignee}")
async def search_by_assignee(
    assignee: str,
    limit: int = 25
):
    """Search USPTO patents by assignee/company name."""
    patents = await uspto_service.get_patents_by_assignee(assignee, limit)
    
    return {
        "assignee": assignee,
        "total": len(patents),
        "patents": [
            {
                "patent_number": p.patent_number,
                "title": p.title,
                "publication_date": str(p.publication_date) if p.publication_date else None
            }
            for p in patents
        ]
    }


@router.get("/uspto/cpc/{cpc_code}")
async def search_by_cpc(
    cpc_code: str,
    start_date: Optional[str] = None,
    limit: int = 25
):
    """
    Search USPTO patents by CPC classification.
    
    Common CPC codes:
    - G06F: Computing/calculating
    - G06N: AI/ML/Neural networks
    - H04L: Network protocols
    - G06Q: Business methods
    - H04W: Wireless communication
    """
    patents = await uspto_service.get_patents_by_cpc(cpc_code, start_date, limit)
    
    return {
        "cpc_code": cpc_code,
        "total": len(patents),
        "patents": [
            {
                "patent_number": p.patent_number,
                "title": p.title,
                "applicant": p.applicant,
                "publication_date": str(p.publication_date) if p.publication_date else None
            }
            for p in patents
        ]
    }
