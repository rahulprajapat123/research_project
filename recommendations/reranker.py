"""
Claim reranker - reranks by credibility, applicability, and recency
"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from loguru import logger

from config import get_settings

settings = get_settings()


class ClaimReranker:
    """Reranks claims based on multiple signals"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def rerank(
        self,
        claims: List[Dict],
        context: Dict[str, Any],
        top_k: int = None
    ) -> List[Dict]:
        """
        Rerank claims by credibility × applicability × recency
        
        Scoring factors:
        - Source credibility score (tier-based)
        - Claim confidence score
        - Recency (decay over time)
        - Validation status (human-validated gets boost)
        - Evidence type strength
        """
        top_k = top_k or settings.rerank_top_k
        
        for claim in claims:
            score = self._calculate_rerank_score(claim, context)
            claim["rerank_score"] = score
        
        # Sort by rerank score
        reranked = sorted(claims, key=lambda x: x["rerank_score"], reverse=True)
        
        # Take top-k
        top_claims = reranked[:top_k]
        
        logger.info(f"Reranked to top {len(top_claims)} claims")
        return top_claims
    
    def _calculate_rerank_score(self, claim: Dict, context: Dict) -> float:
        """Calculate composite rerank score"""
        score = 0.0
        
        # 1. Source credibility (0-45 points normalized to 0-1)
        credibility = claim.get("source_credibility", 0) / 45.0
        score += credibility * 0.3  # 30% weight
        
        # 2. Claim confidence (0-1)
        confidence = claim.get("confidence_score", 0.5)
        score += confidence * 0.25  # 25% weight
        
        # 3. Recency decay (0-1)
        recency = self._calculate_recency_score(claim.get("publication_date"))
        score += recency * 0.15  # 15% weight
        
        # 4. Validation boost (0-1)
        validation_boost = 1.0 if claim.get("extraction_method") == "human_validated" else 0.5
        score += validation_boost * 0.15  # 15% weight
        
        # 5. Evidence strength (0-1)
        evidence_strength = self._get_evidence_strength(claim.get("evidence_type"))
        score += evidence_strength * 0.1  # 10% weight
        
        # 6. Vector similarity (already 0-1)
        similarity = claim.get("similarity", 0.5)
        score += similarity * 0.05  # 5% weight
        
        return score
    
    def _calculate_recency_score(self, publication_date) -> float:
        """Calculate recency score with exponential decay"""
        if not publication_date:
            return 0.5  # Default for unknown dates
        
        try:
            if isinstance(publication_date, str):
                pub_date = datetime.fromisoformat(publication_date)
            else:
                pub_date = publication_date
            
            days_old = (datetime.now() - pub_date).days
            
            # Exponential decay: score = e^(-days / decay_period)
            import math
            decay_period = settings.recency_decay_days
            recency_score = math.exp(-days_old / decay_period)
            
            return max(0.0, min(1.0, recency_score))
            
        except Exception:
            return 0.5
    
    def _get_evidence_strength(self, evidence_type: str) -> float:
        """Map evidence type to strength score"""
        strength_map = {
            "experiment": 1.0,
            "benchmark": 0.9,
            "case_study": 0.7,
            "theoretical": 0.5,
            "anecdotal": 0.3
        }
        return strength_map.get(evidence_type, 0.5)
