"""
RAG Research Intelligence System - Main API Application
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from loguru import logger
import time
from pathlib import Path
import asyncio
import sys

from config import get_settings
from api.routers import briefs, copilot, dashboard, health, intelligence, sources
from ingestion.scheduler import get_scheduler
# Disabled routers (require database): ingestion, recommendations, validation, pipeline

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

settings = get_settings()

# Configure logger
logger.add(
    "logs/api_{time}.log",
    rotation="500 MB",
    retention="10 days",
    level=settings.log_level
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info("All systems ready")
    scheduler = get_scheduler()
    try:
        scheduler.start()
    except Exception as exc:
        logger.warning(f"Scheduler did not start cleanly: {exc}")

    yield

    # Shutdown
    try:
        scheduler.stop()
    except Exception as exc:
        logger.warning(f"Scheduler did not stop cleanly: {exc}")
    logger.info("Shutting down application")


# Initialize FastAPI app
app = FastAPI(
    title="Learning Intelligence Platform",
    description="Upload brief analysis and daily learning intelligence.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(",") if settings.allowed_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
frontend_path = Path(__file__).parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    response.headers["X-Process-Time-Ms"] = str(int(process_time))
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An error occurred"
        }
    )


# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(copilot.router, prefix="/api/v1/copilot", tags=["Research Copilot"])
app.include_router(sources.router, prefix="/api/v1", tags=["Multi-Source Ingestion"])
app.include_router(briefs.router, prefix="/api/v1", tags=["Brief Intelligence"])
app.include_router(intelligence.router, prefix="/api/v1", tags=["Daily Intelligence"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["Dashboard"])
# Disabled routers (require database):
# app.include_router(pipeline.router, prefix="/api/v1", tags=["🚀 Full Pipeline"])
# app.include_router(ingestion.router, prefix="/api/v1", tags=["Ingestion"])
# app.include_router(recommendations.router, prefix="/api/v1", tags=["Recommendations"])
# app.include_router(validation.router, prefix="/api/v1", tags=["Validation"])


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Return 204 No Content for favicon to prevent 404 errors"""
    return Response(status_code=204, media_type="image/x-icon")


@app.get("/")
async def root():
    """Serve Project Research Copilot UI"""
    copilot_page = Path(__file__).parent / "frontend" / "copilot.html"
    if copilot_page.exists():
        return FileResponse(str(copilot_page))
    
    # Fallback to main index
    frontend_index = Path(__file__).parent / "frontend" / "index.html"
    if frontend_index.exists():
        return FileResponse(str(frontend_index))
    
    # Fallback to API info
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    import os
    
    # Railway sets PORT environment variable
    port = int(os.getenv("PORT", settings.api_port))
    
    # Use single worker on Windows due to multiprocessing issues
    workers = 1 if sys.platform.startswith("win") else (1 if settings.debug else settings.api_workers)
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=port,
        reload=settings.debug,
        workers=workers
    )
