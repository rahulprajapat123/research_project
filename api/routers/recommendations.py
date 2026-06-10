"""
Recommendations API endpoints for getting research-backed RAG recommendations
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session

from database.connection import get_db
from recommendations.retriever import ClaimRetriever
from recommendations.reranker import ClaimReranker
from recommendations.generator import RecommendationGenerator
from loguru import logger

router = APIRouter()


class ProjectContext(BaseModel):
    """Project-specific context for generating recommendations"""
    project_name: str = Field(..., description="Name of the RAG project")
    use_case: str = Field(..., description="Primary use case (e.g., 'customer support', 'legal research', 'code search')")
    data_characteristics: Dict[str, Any] = Field(
        ...,
        description="Data properties: document_types, avg_document_length, domain, language"
    )
    constraints: Dict[str, Any] = Field(
        default_factory=dict,
        description="Constraints: budget, latency_requirements, scale, existing_infrastructure"
    )
    current_challenges: Optional[List[str]] = Field(
        default=None,
        description="Current pain points or challenges"
    )
    rag_components_of_interest: List[str] = Field(
        default=["retrieval", "chunking", "embedding", "reranking"],
        description="Which RAG components to focus on"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_name": "Customer Support RAG System",
                "use_case": "customer_support",
                "data_characteristics": {
                    "document_types": ["pdf", "html", "markdown"],
                    "avg_document_length": 2000,
                    "domain": "technical_documentation",
                    "language": "english"
                },
                "constraints": {
                    "budget": "moderate",
                    "latency_requirements": "< 2 seconds",
                    "scale": "100k documents"
                },
                "current_challenges": [
                    "Low recall on technical queries",
                    "Inconsistent chunk boundaries"
                ],
                "rag_components_of_interest": ["chunking", "retrieval", "reranking"]
            }
        }


class Recommendation(BaseModel):
    """Single recommendation with supporting evidence"""
    technique: str
    description: str
    rationale: str
    supporting_claims: List[Dict[str, Any]]
    implementation_priority: str  # high, medium, low
    estimated_impact: str


class RecommendationResponse(BaseModel):
    """Response model for recommendations"""
    project_context: ProjectContext
    recommendations: List[Recommendation]
    summary: str
    citations: List[Dict[str, str]]
    retrieval_metrics: Dict[str, Any]


class FeedbackRequest(BaseModel):
    """Feedback payload for a recommendation"""
    feedback: str  # helpful | not_helpful | partially_helpful
    notes: Optional[str] = None


@router.post("/recommend", response_model=RecommendationResponse)
async def get_recommendations(
    context: ProjectContext,
    top_k: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get research-backed recommendations for a RAG project
    
    This endpoint:
    1. Validates project context (strict schema enforcement)
    2. Retrieves relevant claims (vector + keyword hybrid search)
    3. Re-ranks by credibility × applicability × recency
    4. Generates actionable recommendations with citations
    """
    try:
        logger.info(f"Generating recommendations for: {context.project_name}")
        
        # Step 1: Retrieve relevant claims
        retriever = ClaimRetriever(db)
        retrieved_claims = await retriever.retrieve(
            query_text=f"{context.use_case} {' '.join(context.rag_components_of_interest)}",
            filters={
                "rag_applicability": context.rag_components_of_interest
            },
            top_k=top_k
        )
        
        if not retrieved_claims:
            raise HTTPException(
                status_code=404,
                detail="No relevant claims found. Database may be empty or query too specific."
            )
        
        # Step 2: Re-rank claims
        reranker = ClaimReranker(db)
        reranked_claims = reranker.rerank(
            claims=retrieved_claims,
            context=context.dict(),
            top_k=10
        )
        
        # Step 3: Generate recommendations
        generator = RecommendationGenerator(db)
        response = await generator.generate(
            claims=reranked_claims,
            context=context
        )
        
        # Log recommendation for analytics
        from sqlalchemy import text
        db.execute(
            text("""
                INSERT INTO recommendation_logs 
                (project_context, retrieved_claim_ids, reranked_claim_ids, 
                 final_recommendation, reasoning, citations, retrieval_metrics, 
                 llm_model, response_time_ms)
                VALUES (:context, :retrieved, :reranked, :recommendation, 
                        :reasoning, :citations, :metrics, :model, :time_ms)
            """),
            {
                "context": context.json(),
                "retrieved": [str(c["id"]) for c in retrieved_claims],
                "reranked": [str(c["id"]) for c in reranked_claims],
                "recommendation": response["summary"],
                "reasoning": response.get("reasoning"),
                "citations": str(response["citations"]),
                "metrics": str(response["retrieval_metrics"]),
                "model": response.get("llm_model"),
                "time_ms": response.get("response_time_ms")
            }
        )
        db.commit()
        
        return RecommendationResponse(**response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recommendation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations/{recommendation_id}/feedback")
async def submit_feedback(
    recommendation_id: UUID,
    payload: FeedbackRequest,
    db: Session = Depends(get_db)
):
    """Submit user feedback on a recommendation"""
    from sqlalchemy import text
    
    if payload.feedback not in ["helpful", "not_helpful", "partially_helpful"]:
        raise HTTPException(status_code=400, detail="Invalid feedback value")
    
    result = db.execute(
        text("""
            UPDATE recommendation_logs 
            SET user_feedback = :feedback, user_feedback_notes = :notes
            WHERE id = :rec_id
            RETURNING id
        """),
        {"feedback": payload.feedback, "notes": payload.notes, "rec_id": str(recommendation_id)}
    )
    
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    db.commit()
    
    return {"status": "success", "message": "Feedback recorded"}
