"""
End-to-End Pipeline API - Full automation from project brief to recommendations
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from datetime import datetime

from database.connection import get_db
from ingestion.coordinator import IngestCoordinator
from recommendations.retriever import ClaimRetriever
from recommendations.reranker import ClaimReranker
from recommendations.generator import RecommendationGenerator
from loguru import logger

router = APIRouter()


class ProjectBrief(BaseModel):
    """Complete project brief for automated pipeline"""
    # Project Context
    project_name: str = Field(..., description="Name of your RAG project")
    use_case: str = Field(..., description="e.g., customer_support, legal_research, code_search")
    
    # Data Characteristics
    document_types: List[str] = Field(default=["pdf", "html"], description="Types of documents")
    avg_document_length: int = Field(default=2000, description="Average document length in words")
    domain: str = Field(default="general", description="Domain/industry")
    language: str = Field(default="english")
    
    # Constraints
    budget: str = Field(default="moderate", description="low, moderate, high")
    latency_requirements: str = Field(default="< 5 seconds")
    scale: str = Field(default="100k documents")
    existing_infrastructure: Optional[str] = None
    
    # Current Challenges
    current_challenges: List[str] = Field(default_factory=list)
    
    # RAG Components
    rag_components_of_interest: List[str] = Field(
        default=["retrieval", "chunking", "embedding", "reranking"],
        description="Components to optimize"
    )
    
    # Optional: Auto-ingest research sources
    auto_ingest_sources: Optional[List[HttpUrl]] = Field(
        default=None,
        description="Automatically ingest these research papers/sources"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_name": "Legal Document RAG System",
                "use_case": "legal_research",
                "document_types": ["pdf", "docx"],
                "avg_document_length": 5000,
                "domain": "legal",
                "budget": "high",
                "latency_requirements": "< 3 seconds",
                "scale": "500k documents",
                "current_challenges": [
                    "Long documents require better chunking",
                    "Need to maintain legal citations accurately"
                ],
                "rag_components_of_interest": ["chunking", "retrieval", "citation_preservation"],
                "auto_ingest_sources": [
                    "https://arxiv.org/abs/2401.12345",
                    "https://arxiv.org/abs/2312.10997"
                ]
            }
        }


class PipelineStatus(BaseModel):
    """Status of the automated pipeline execution"""
    pipeline_id: str
    status: str
    project_name: str
    steps_completed: List[str]
    steps_remaining: List[str]
    ingested_sources: List[Dict[str, Any]]
    extracted_claims_count: int
    recommendations_ready: bool
    recommendations: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    estimated_completion_time: Optional[str] = None


@router.post("/pipeline/execute", response_model=Dict[str, Any])
async def execute_full_pipeline(
    brief: ProjectBrief,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    🚀 FULL AUTOMATED PIPELINE
    
    Give me your project brief, and I'll:
    1. Auto-ingest relevant research sources (if provided)
    2. Parse documents → Extract claims
    3. Store in knowledge base with embeddings
    4. Generate research-backed recommendations
    
    This is the ONE endpoint you need!
    """
    try:
        pipeline_id = f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"🚀 Starting automated pipeline for: {brief.project_name}")
        
        # Step 1: Auto-ingest sources if provided
        ingested_sources = []
        if brief.auto_ingest_sources and len(brief.auto_ingest_sources) > 0:
            logger.info(f"📥 Step 1: Auto-ingesting {len(brief.auto_ingest_sources)} sources")
            coordinator = IngestCoordinator(db)
            
            for source_url in brief.auto_ingest_sources:
                try:
                    source_id = coordinator.create_source_entry(
                        url=str(source_url),
                        title=f"Auto-ingested for {brief.project_name}",
                        source_type="arxiv" if "arxiv" in str(source_url) else "blog",
                        tier="A",
                        credibility_score=75
                    )
                    
                    # Process in background
                    background_tasks.add_task(
                        coordinator.process_document_pipeline,
                        source_id
                    )
                    
                    ingested_sources.append({
                        "source_id": str(source_id),
                        "url": str(source_url),
                        "status": "processing"
                    })
                    
                    logger.info(f"✅ Queued: {source_url}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to ingest {source_url}: {e}")
                    ingested_sources.append({
                        "url": str(source_url),
                        "status": "failed",
                        "error": str(e)
                    })
        
        # Step 2: Generate recommendations from existing knowledge base
        logger.info(f"💡 Step 2: Generating recommendations")
        
        project_context = {
            "project_name": brief.project_name,
            "use_case": brief.use_case,
            "data_characteristics": {
                "document_types": brief.document_types,
                "avg_document_length": brief.avg_document_length,
                "domain": brief.domain,
                "language": brief.language
            },
            "constraints": {
                "budget": brief.budget,
                "latency_requirements": brief.latency_requirements,
                "scale": brief.scale,
                "existing_infrastructure": brief.existing_infrastructure
            },
            "current_challenges": brief.current_challenges,
            "rag_components_of_interest": brief.rag_components_of_interest
        }
        
        # Retrieve relevant claims
        retriever = ClaimRetriever(db)
        query_text = f"{brief.use_case} {brief.domain} {' '.join(brief.rag_components_of_interest)}"
        
        retrieved_claims = await retriever.retrieve(
            query_text=query_text,
            filters={"rag_applicability": brief.rag_components_of_interest},
            top_k=20
        )
        
        recommendations_data = None
        if retrieved_claims and len(retrieved_claims) > 0:
            # Re-rank claims
            reranker = ClaimReranker(db)
            reranked_claims = reranker.rerank(
                claims=retrieved_claims,
                context=project_context,
                top_k=10
            )
            
            # Generate recommendations
            generator = RecommendationGenerator(db)
            recommendations_response = await generator.generate(
                claims=reranked_claims,
                context=project_context
            )
            
            recommendations_data = recommendations_response
            logger.info(f"✅ Generated {len(recommendations_response.get('recommendations', []))} recommendations")
        else:
            logger.warning("⚠️  No existing claims in knowledge base. Recommendations will be generated after ingestion completes.")
        
        # Return complete pipeline status
        return {
            "pipeline_id": pipeline_id,
            "status": "processing" if ingested_sources else "completed",
            "message": "Pipeline executing. Check back for updated recommendations as sources are processed." if ingested_sources else "Recommendations generated from existing knowledge base.",
            "project_brief": {
                "project_name": brief.project_name,
                "use_case": brief.use_case,
                "domain": brief.domain
            },
            "pipeline_steps": {
                "step_1_ingestion": {
                    "status": "processing" if ingested_sources else "skipped",
                    "sources_queued": len(ingested_sources),
                    "sources": ingested_sources
                },
                "step_2_normalization": {
                    "status": "will_process_after_ingestion" if ingested_sources else "skipped",
                    "description": "Parse documents → Extract claims → Generate embeddings"
                },
                "step_3_knowledge_store": {
                    "status": "available",
                    "claims_retrieved": len(retrieved_claims) if retrieved_claims else 0
                },
                "step_4_recommendations": {
                    "status": "completed" if recommendations_data else "waiting_for_claims",
                    "recommendations": recommendations_data.get("recommendations", []) if recommendations_data else [],
                    "summary": recommendations_data.get("summary") if recommendations_data else None,
                    "citations": recommendations_data.get("citations", []) if recommendations_data else []
                }
            },
            "next_steps": [
                "Monitor ingestion status at /api/v1/sources" if ingested_sources else None,
                "Review validation queue at /api/v1/validation/queue" if ingested_sources else None,
                "Approve/reject extracted claims for quality control" if ingested_sources else None,
                "Re-run pipeline after claims are validated for updated recommendations" if ingested_sources else None
            ],
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Pipeline execution error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipeline/status/{pipeline_id}")
async def get_pipeline_status(
    pipeline_id: str,
    db: Session = Depends(get_db)
):
    """
    Check the status of a running pipeline
    """
    # This would query a pipeline_runs table in production
    return {
        "pipeline_id": pipeline_id,
        "status": "Use /api/v1/sources to check ingestion status",
        "message": "Pipeline status tracking coming soon!"
    }


@router.post("/pipeline/quick-recommend")
async def quick_recommend(
    brief: ProjectBrief,
    db: Session = Depends(get_db)
):
    """
    🎯 QUICK RECOMMENDATIONS (No ingestion, uses existing knowledge base only)
    
    Get immediate recommendations from existing knowledge base.
    Use this when you don't need to ingest new sources.
    """
    try:
        logger.info(f"⚡ Quick recommendation for: {brief.project_name}")
        
        project_context = {
            "project_name": brief.project_name,
            "use_case": brief.use_case,
            "data_characteristics": {
                "document_types": brief.document_types,
                "avg_document_length": brief.avg_document_length,
                "domain": brief.domain,
                "language": brief.language
            },
            "constraints": {
                "budget": brief.budget,
                "latency_requirements": brief.latency_requirements,
                "scale": brief.scale,
                "existing_infrastructure": brief.existing_infrastructure
            },
            "current_challenges": brief.current_challenges,
            "rag_components_of_interest": brief.rag_components_of_interest
        }
        
        # Retrieve and rerank
        retriever = ClaimRetriever(db)
        query_text = f"{brief.use_case} {brief.domain} {' '.join(brief.rag_components_of_interest)}"
        
        retrieved_claims = await retriever.retrieve(
            query_text=query_text,
            filters={"rag_applicability": brief.rag_components_of_interest},
            top_k=20
        )
        
        if not retrieved_claims or len(retrieved_claims) == 0:
            raise HTTPException(
                status_code=404,
                detail="No claims in knowledge base yet. Use /pipeline/execute with auto_ingest_sources to populate the database first."
            )
        
        reranker = ClaimReranker(db)
        reranked_claims = reranker.rerank(
            claims=retrieved_claims,
            context=project_context,
            top_k=10
        )
        
        # Generate recommendations
        generator = RecommendationGenerator(db)
        response = await generator.generate(
            claims=reranked_claims,
            context=project_context
        )
        
        return {
            "project_context": project_context,
            "recommendations": response.get("recommendations", []),
            "summary": response.get("summary"),
            "citations": response.get("citations", []),
            "retrieval_metrics": {
                "claims_retrieved": len(retrieved_claims),
                "claims_reranked": len(reranked_claims)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quick recommend error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
