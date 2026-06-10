"""
Ingestion API endpoints for receiving and processing documents
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
from datetime import date
from uuid import UUID
from sqlalchemy.orm import Session

from database.connection import get_db
from ingestion.coordinator import IngestCoordinator
from ingestion.source_classifier import classify_source_tier, is_source_allowed
from loguru import logger

router = APIRouter()


class IngestDocumentRequest(BaseModel):
    """Request model for document ingestion"""
    url: HttpUrl
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    publication_date: Optional[date] = None
    source_type: str = Field(..., description="arxiv, blog, benchmark, vendor_announcement")
    citation_count: Optional[int] = None
    author_h_index: Optional[int] = None
    metadata: dict = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://arxiv.org/abs/2401.12345",
                "title": "Advanced RAG Techniques for Production Systems",
                "authors": ["John Doe", "Jane Smith"],
                "publication_date": "2024-01-15",
                "source_type": "arxiv",
                "citation_count": 45,
                "metadata": {"arxiv_id": "2401.12345"}
            }
        }


class IngestDocumentResponse(BaseModel):
    """Response model for document ingestion"""
    source_id: UUID
    status: str
    tier: str
    credibility_score: int
    message: str


@router.post("/ingest", response_model=IngestDocumentResponse)
async def ingest_document(
    request: IngestDocumentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Ingest a new research document for processing
    
    This endpoint:
    1. Validates the source URL
    2. Classifies source tier and credibility
    3. Downloads and stores the document
    4. Queues for parsing and claim extraction
    """
    try:
        if not is_source_allowed(str(request.url)):
            raise HTTPException(status_code=400, detail="Source domain is not allowed")
        
        # Classify source tier
        tier, credibility_score = classify_source_tier(
            str(request.url),
            request.citation_count,
            request.author_h_index
        )
        
        logger.info(f"Ingesting document: {request.url} (Tier: {tier}, Score: {credibility_score})")
        
        # Create coordinator and process
        coordinator = IngestCoordinator(db)
        source_id = coordinator.create_source_entry(
            url=str(request.url),
            title=request.title,
            authors=request.authors,
            publication_date=request.publication_date,
            source_type=request.source_type,
            tier=tier,
            credibility_score=credibility_score,
            citation_count=request.citation_count,
            author_h_index=request.author_h_index,
            metadata=request.metadata
        )
        
        # Process in background
        background_tasks.add_task(
            coordinator.process_document_pipeline,
            source_id
        )
        
        return IngestDocumentResponse(
            source_id=source_id,
            status="processing",
            tier=tier,
            credibility_score=credibility_score,
            message="Document queued for processing"
        )
        
    except Exception as e:
        logger.error(f"Ingestion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources/{source_id}")
async def get_source_status(source_id: UUID, db: Session = Depends(get_db)):
    """Get ingestion status and details for a specific source"""
    from sqlalchemy import text
    
    result = db.execute(
        text("""
            SELECT id, url, title, tier, credibility_score, ingestion_status, created_at, updated_at
            FROM sources
            WHERE id = :source_id
        """),
        {"source_id": str(source_id)}
    ).mappings().fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Source not found")
    
    # Get associated claims
    claims = db.execute(
        text("SELECT COUNT(*) FROM claims WHERE source_id = :source_id"),
        {"source_id": str(source_id)}
    ).scalar()
    
    return {
        "source_id": result["id"],
        "url": result["url"],
        "title": result["title"],
        "status": result["ingestion_status"],
        "tier": result["tier"],
        "credibility_score": result["credibility_score"],
        "claims_extracted": claims,
        "created_at": result["created_at"],
        "updated_at": result["updated_at"]
    }


@router.get("/sources")
async def list_sources(
    skip: int = 0,
    limit: int = 50,
    tier: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all ingested sources with optional filters"""
    from sqlalchemy import text
    
    query = "SELECT id, url, title, tier, credibility_score, ingestion_status, created_at FROM sources"
    filters = []
    params = {"skip": skip, "limit": limit}
    
    if tier:
        filters.append("tier = :tier")
        params["tier"] = tier
    
    if status:
        filters.append("ingestion_status = :status")
        params["status"] = status
    
    if filters:
        query += " WHERE " + " AND ".join(filters)
    
    query += " ORDER BY created_at DESC OFFSET :skip LIMIT :limit"
    
    results = db.execute(text(query), params).fetchall()
    
    return {
        "sources": [
            {
                "id": r[0],
                "url": r[1],
                "title": r[2],
                "tier": r[3],
                "credibility_score": r[4],
                "status": r[5],
                "created_at": r[6]
            }
            for r in results
        ],
        "skip": skip,
        "limit": limit
    }
