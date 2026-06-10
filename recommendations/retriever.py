"""
Claim retriever - hybrid vector + keyword search
"""
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from loguru import logger

from utils.embedding_client import EmbeddingClient
from config import get_settings

settings = get_settings()


class ClaimRetriever:
    """Retrieves relevant claims using hybrid search"""
    
    def __init__(self, db: Session):
        self.db = db
        self.embedder = EmbeddingClient()
    
    async def retrieve(
        self,
        query_text: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = None
    ) -> List[Dict]:
        """
        Retrieve relevant claims using hybrid search
        
        Args:
            query_text: User query or project description
            filters: Optional filters (rag_applicability, evidence_type, etc.)
            top_k: Number of results to return
        
        Returns:
            List of claim dictionaries with metadata
        """
        top_k = top_k or settings.default_top_k
        
        # Generate query embedding
        query_embedding = await self.embedder.embed(query_text)
        
        # Build SQL query with filters
        sql_query = """
            WITH vector_results AS (
                SELECT 
                    c.id,
                    c.claim_text,
                    c.evidence_type,
                    c.evidence_location,
                    c.metrics,
                    c.conditions,
                    c.limitations,
                    c.rag_applicability,
                    c.confidence_score,
                    c.extraction_method,
                    s.url as source_url,
                    s.title as source_title,
                    s.tier as source_tier,
                    s.credibility_score as source_credibility,
                    s.publication_date,
                    1 - (c.embedding <=> :query_embedding::vector) as similarity
                FROM claims c
                JOIN sources s ON c.source_id = s.id
                WHERE c.confidence_score >= :min_confidence
        """
        
        params = {
            "query_embedding": query_embedding,
            "min_confidence": settings.min_claim_confidence,
            "top_k": top_k
        }
        
        # Add filters
        if filters:
            if "rag_applicability" in filters:
                applicabilities = filters["rag_applicability"]
                if isinstance(applicabilities, list):
                    placeholders = ", ".join([f":app_{i}" for i in range(len(applicabilities))])
                    sql_query += f" AND c.rag_applicability IN ({placeholders})"
                    for i, app in enumerate(applicabilities):
                        params[f"app_{i}"] = app
            
            if "evidence_type" in filters:
                sql_query += " AND c.evidence_type = :evidence_type"
                params["evidence_type"] = filters["evidence_type"]
            
            if "tier" in filters:
                sql_query += " AND s.tier = :tier"
                params["tier"] = filters["tier"]
        
        sql_query += """
            ORDER BY similarity DESC
            LIMIT :top_k
        )
        SELECT * FROM vector_results
        """
        
        results = self.db.execute(text(sql_query), params).fetchall()
        
        claims = []
        for row in results:
            claims.append({
                "id": row[0],
                "claim_text": row[1],
                "evidence_type": row[2],
                "evidence_location": row[3],
                "metrics": row[4],
                "conditions": row[5],
                "limitations": row[6],
                "rag_applicability": row[7],
                "confidence_score": row[8],
                "extraction_method": row[9],
                "source_url": row[10],
                "source_title": row[11],
                "source_tier": row[12],
                "source_credibility": row[13],
                "publication_date": row[14],
                "similarity": row[15]
            })
        
        logger.info(f"Retrieved {len(claims)} claims for query: {query_text[:50]}...")
        return claims
