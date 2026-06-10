"""Dashboard, research feed, technology radar, and recommendation detail APIs."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from research_intelligence.store import get_store


router = APIRouter()


@router.get("/dashboard/overview")
async def dashboard_overview() -> Dict[str, Any]:
    return get_store().dashboard_overview()


@router.get("/technology-radar")
async def technology_radar() -> Dict[str, Any]:
    return {"technologies": get_store().get_technology_radar()}


@router.get("/research-feed")
async def research_feed(
    q: Optional[str] = None,
    source_type: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    return {"items": get_store().get_research_feed(query=q, source_type=source_type, limit=limit)}


@router.get("/recommendations/{recommendation_id}")
async def recommendation_detail(recommendation_id: str) -> Dict[str, Any]:
    recommendation = get_store().get_recommendation(recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return recommendation

