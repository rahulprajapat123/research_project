"""
Validation queue manager - handles human-in-the-loop validation
"""
from typing import List, Dict
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import text
from loguru import logger

from config import get_settings

settings = get_settings()


class ValidationQueue:
    """Manages claim validation queue and sampling logic"""
    
    def __init__(self, db: Session):
        self.db = db
        self.total_validated = self._get_total_validated()
    
    def _get_total_validated(self) -> int:
        """Get total number of claims validated so far"""
        result = self.db.execute(
            text("""
                SELECT COUNT(*) FROM claims 
                WHERE extraction_method IN ('human_validated', 'human_edited')
            """)
        ).scalar()
        return result or 0
    
    async def enqueue_for_validation(
        self,
        source_id: UUID,
        claims: List[Dict]
    ):
        """
        Enqueue claims for validation based on sampling rules
        
        Rules:
        - First 100 claims: 100% validation required
        - After 100: sample at configured rate (default 10%)
        - Low confidence claims (<0.6): always validate
        - Conflicting claims: always validate
        """
        for claim in claims:
            should_validate, reason, priority = self._should_validate(claim)
            
            if should_validate:
                claim_id = claim.get("claim_id")
                if not claim_id:
                    logger.warning("Skipping validation enqueue: missing claim_id")
                    continue
                self._add_to_queue(
                    claim_id=claim_id,
                    reason=reason,
                    priority=priority
                )
    
    def _should_validate(self, claim: Dict) -> tuple[bool, str, int]:
        """
        Determine if claim should be validated
        
        Returns (should_validate, reason, priority)
        """
        # Always validate first 100 claims
        if self.total_validated < 100:
            return (True, "initial_100", 10)
        
        # Always validate low confidence
        if claim.get("confidence_score", 1.0) < settings.min_claim_confidence:
            return (True, "low_confidence", 8)
        
        # Always validate if conflict detected
        if claim.get("has_conflict", False):
            return (True, "conflict", 9)
        
        # Sample at configured rate
        import random
        if random.random() < settings.human_validation_sample_rate:
            return (True, "sampling", 5)
        
        # No validation needed
        return (False, "none", 0)
    
    def _add_to_queue(
        self,
        claim_id: UUID,
        reason: str,
        priority: int
    ):
        """Add claim to validation queue"""
        validation_id = uuid4()
        
        self.db.execute(
            text("""
                INSERT INTO validation_queue
                (id, claim_id, priority, reason, status)
                VALUES (:id, :claim_id, :priority, :reason, 'pending')
            """),
            {
                "id": str(validation_id),
                "claim_id": str(claim_id),
                "priority": priority,
                "reason": reason
            }
        )
        self.db.commit()
        
        logger.debug(f"Added claim {claim_id} to validation queue (reason: {reason}, priority: {priority})")
    
    async def send_validation_notification(self, claim_ids: List[UUID]):
        """
        Send notification to n8n/Slack for claims requiring validation
        
        This triggers the human review workflow
        """
        if not claim_ids:
            return
        
        # Send to n8n webhook
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.n8n_validation_webhook_url,
                    json={
                        "event": "validation_required",
                        "claim_ids": [str(cid) for cid in claim_ids],
                        "count": len(claim_ids)
                    },
                    timeout=10
                )
                response.raise_for_status()
                logger.info(f"Sent validation notification for {len(claim_ids)} claims")
        
        except Exception as e:
            logger.error(f"Failed to send validation notification: {e}")
    
    def get_pending_count(self) -> int:
        """Get count of pending validations"""
        return self.db.execute(
            text("SELECT COUNT(*) FROM validation_queue WHERE status = 'pending'")
        ).scalar() or 0
