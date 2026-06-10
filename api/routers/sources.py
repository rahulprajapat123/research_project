"""
Multi-source metadata ingestion API endpoints.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field, field_validator

from ingestion.source_orchestrator import KNOWN_SOURCES, SourceOrchestrator

router = APIRouter()


class FetchRequest(BaseModel):
    keywords: Optional[List[str]] = Field(default=None, description="Search keywords")
    enable_apify: bool = Field(default=False, description="Enable Apify-backed scrapers")
    sources: Optional[List[str]] = Field(default=None, description="Specific source ids to fetch")

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return value
        unknown = sorted(source for source in value if source not in KNOWN_SOURCES)
        if unknown:
            raise ValueError(f"Unsupported sources: {', '.join(unknown)}")
        return value


class FetchResponse(BaseModel):
    status: str
    message: str
    documents_fetched: int
    fetch_timestamp: str
    sources_used: List[str]


@router.post("/sources/fetch", response_model=FetchResponse, tags=["Multi-Source Ingestion"])
async def fetch_from_all_sources(request: FetchRequest) -> FetchResponse:
    try:
        result = await SourceOrchestrator().fetch_and_store(
            keywords=request.keywords,
            enable_apify=request.enable_apify,
            sources=request.sources,
        )
    except Exception as exc:
        logger.error(f"Multi-source fetch failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return FetchResponse(
        status="success",
        message=(
            f"Fetched {result['items_fetched']} unique documents from "
            f"{len(result['sources_used'])} sources"
        ),
        documents_fetched=result["items_fetched"],
        fetch_timestamp=datetime.utcnow().isoformat(),
        sources_used=result["sources_used"],
    )


@router.post("/sources/fetch-latest", response_model=FetchResponse, tags=["Multi-Source Ingestion"])
async def fetch_latest_sources(request: FetchRequest) -> FetchResponse:
    """Alias used by the dashboard for manual latest-source refreshes."""
    return await fetch_from_all_sources(request)


@router.get("/sources/status", tags=["Multi-Source Ingestion"])
async def get_sources_status() -> dict:
    from config import get_settings

    current_settings = get_settings()
    return {
        "research_sources": {
            "arxiv": {"enabled": True, "requires_key": False},
            "semantic_scholar": {
                "enabled": bool(current_settings.semantic_scholar_api_key),
                "requires_key": True,
            },
            "openalex": {"enabled": True, "requires_key": False},
        },
        "news_sources": {
            "gnews": {"enabled": bool(current_settings.gnews_api_key), "requires_key": True},
            "newsapi": {"enabled": bool(current_settings.newsapi_key), "requires_key": True},
            "rss": {"enabled": True, "feed_count": len(current_settings.rss_feeds)},
            "google_news": {"enabled": True, "requires_key": False},
            "exa": {"enabled": bool(current_settings.exa_api_key), "requires_key": True},
        },
        "developer_sources": {
            "github": {"enabled": True, "authenticated": bool(current_settings.github_token)},
            "hackernews": {"enabled": True, "requires_key": False},
        },
        "scrapers": {
            "apify_google_news": {
                "enabled": bool(current_settings.apify_api_token),
                "requires_key": True,
            }
        },
        "known_source_ids": sorted(KNOWN_SOURCES),
    }


@router.get("/sources/management", tags=["Multi-Source Ingestion"])
async def get_source_management() -> dict:
    from research_intelligence.store import get_store

    return get_store().source_management()


@router.get("/sources/stats", tags=["Multi-Source Ingestion"])
async def get_fetch_stats() -> dict:
    try:
        return SourceOrchestrator().get_fetch_stats()
    except Exception as exc:
        logger.error(f"Fetch stats query failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
