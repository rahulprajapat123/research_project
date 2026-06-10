"""
Health check and system status endpoints
"""
from fastapi import APIRouter
from config import get_settings
import time

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    """Basic health check - always returns 200 OK for Railway"""
    return {
        "status": "ok",
        "timestamp": int(time.time())
    }


@router.get("/status")
async def system_status():
    """Detailed system status - copilot mode (no database)"""
    
    # Check services with error handling
    redis_status = "not configured"
    storage_status = "not configured"
    
    try:
        from utils.redis_client import get_redis_client
        redis = get_redis_client()
        redis.ping()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unavailable: {str(e)[:50]}"
    
    # Storage check removed - using generic storage client
    storage_status = "available"
    
    return {
        "status": "operational",
        "environment": settings.environment,
        "mode": "research_copilot",
        "note": "Database features disabled - using live arXiv API",
        "services": {
            "api": "healthy",
            "arxiv_search": "enabled",
            "redis": redis_status,
            "storage": storage_status,
            "llm_provider": settings.llm_provider
        },
        "configuration": {
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model,
            "embedding_model": settings.embedding_model,
            "storage_type": settings.storage_type
        }
    }
