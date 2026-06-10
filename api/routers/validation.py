"""
Validation API endpoints for human-in-the-loop claim validation
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from database.connection import get_db
from loguru import logger

router = APIRouter()


class ValidationItem(BaseModel):
    """Validation queue item"""
    id: UUID
    claim_id: UUID
    claim_text: str
    evidence_type: str
    evidence_location: Optional[str]
    confidence_score: float
    source_title: Optional[str]
    source_url: str
    priority: int
    reason: str


class ValidationDecision(BaseModel):
    """Validation decision from reviewer"""
    decision: str  # approved, rejected, edited
    edited_claim_text: Optional[str] = None
    edited_evidence_location: Optional[str] = None
    edited_confidence_score: Optional[float] = None
    reviewer_notes: Optional[str] = None


@router.get("/validation/queue", response_model=List[ValidationItem])
async def get_validation_queue(
    assigned_to: Optional[str] = None,
    priority_min: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get pending validation items
    
    Returns claims that require human review, sorted by priority
    """
    from sqlalchemy import text
    
    query = """
        SELECT 
            vq.id,
            vq.claim_id,
            c.claim_text,
            c.evidence_type,
            c.evidence_location,
            c.confidence_score,
            s.title as source_title,
            s.url as source_url,
            vq.priority,
            vq.reason
        FROM validation_queue vq
        JOIN claims c ON vq.claim_id = c.id
        JOIN sources s ON c.source_id = s.id
        WHERE vq.status = 'pending'
    """
    
    params = {"limit": limit, "priority_min": priority_min}
    
    if assigned_to:
        query += " AND vq.assigned_to = :assigned_to"
        params["assigned_to"] = assigned_to
    
    query += " AND vq.priority >= :priority_min"
    query += " ORDER BY vq.priority DESC, vq.created_at ASC LIMIT :limit"
    
    results = db.execute(text(query), params).fetchall()
    
    return [
        ValidationItem(
            id=r[0],
            claim_id=r[1],
            claim_text=r[2],
            evidence_type=r[3],
            evidence_location=r[4],
            confidence_score=r[5],
            source_title=r[6],
            source_url=r[7],
            priority=r[8],
            reason=r[9]
        )
        for r in results
    ]


@router.post("/validation/{validation_id}/submit")
async def submit_validation(
    validation_id: UUID,
    decision: ValidationDecision,
    reviewer: str,
    db: Session = Depends(get_db)
):
    """
    Submit validation decision for a claim
    
    Updates the claim with human validation and removes from queue
    """
    from sqlalchemy import text
    import time
    
    try:
        # Get the claim_id from validation queue
        result = db.execute(
            text("SELECT claim_id FROM validation_queue WHERE id = :id"),
            {"id": str(validation_id)}
        ).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Validation item not found")
        
        claim_id = result[0]
        
        # Update claim based on decision
        if decision.decision == "approved":
            db.execute(
                text("""
                    UPDATE claims 
                    SET extraction_method = 'human_validated',
                        validated_by = :reviewer,
                        validated_at = NOW(),
                        validation_notes = :notes
                    WHERE id = :claim_id
                """),
                {
                    "reviewer": reviewer,
                    "notes": decision.reviewer_notes,
                    "claim_id": claim_id
                }
            )
        
        elif decision.decision == "edited":
            db.execute(
                text("""
                    UPDATE claims 
                    SET claim_text = COALESCE(:edited_text, claim_text),
                        evidence_location = COALESCE(:edited_location, evidence_location),
                        confidence_score = COALESCE(:edited_score, confidence_score),
                        extraction_method = 'human_edited',
                        validated_by = :reviewer,
                        validated_at = NOW(),
                        validation_notes = :notes
                    WHERE id = :claim_id
                """),
                {
                    "edited_text": decision.edited_claim_text,
                    "edited_location": decision.edited_evidence_location,
                    "edited_score": decision.edited_confidence_score,
                    "reviewer": reviewer,
                    "notes": decision.reviewer_notes,
                    "claim_id": claim_id
                }
            )
        
        elif decision.decision == "rejected":
            # Delete the claim
            db.execute(
                text("DELETE FROM claims WHERE id = :claim_id"),
                {"claim_id": claim_id}
            )
        
        # Update validation queue
        db.execute(
            text("""
                UPDATE validation_queue 
                SET status = :status,
                    reviewer_notes = :notes,
                    reviewed_at = NOW()
                WHERE id = :id
            """),
            {
                "status": decision.decision,
                "notes": decision.reviewer_notes,
                "id": str(validation_id)
            }
        )
        
        db.commit()
        
        logger.info(f"Validation {validation_id} processed: {decision.decision} by {reviewer}")
        
        return {
            "status": "success",
            "validation_id": validation_id,
            "decision": decision.decision,
            "message": f"Claim {decision.decision}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Validation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/validation/stats")
async def get_validation_stats(db: Session = Depends(get_db)):
    """Get validation queue statistics"""
    from sqlalchemy import text
    
    stats = {}
    
    # Pending count
    stats["pending"] = db.execute(
        text("SELECT COUNT(*) FROM validation_queue WHERE status = 'pending'")
    ).scalar()
    
    # Completed today
    stats["completed_today"] = db.execute(
        text("""
            SELECT COUNT(*) FROM validation_queue 
            WHERE status IN ('approved', 'rejected', 'edited')
            AND reviewed_at >= CURRENT_DATE
        """)
    ).scalar()
    
    # By reason
    reason_counts = db.execute(
        text("""
            SELECT reason, COUNT(*) 
            FROM validation_queue 
            WHERE status = 'pending'
            GROUP BY reason
        """)
    ).fetchall()
    
    stats["by_reason"] = {r[0]: r[1] for r in reason_counts}
    
    return stats
