"""Project brief upload and recommendation APIs."""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, File, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel

from research_intelligence.brief_service import BriefIntelligenceService
from research_intelligence.parsing import BriefParsingError


router = APIRouter()


class BriefUploadResponse(BaseModel):
    brief_id: str
    file_name: str
    file_type: str
    processing_status: str
    parsed_summary: str
    extracted_topics: List[Dict[str, Any]]
    project_profile: Dict[str, Any]


@router.post("/briefs/upload", response_model=BriefUploadResponse)
async def upload_brief(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Upload and parse a project brief, PRD, PDF, markdown, text, or DOCX file."""
    try:
        content = await file.read()
        return await BriefIntelligenceService().upload_brief(file.filename or "brief.txt", content)
    except BriefParsingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Brief upload failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Brief upload failed") from exc


@router.get("/briefs/{brief_id}")
async def get_brief(brief_id: str) -> Dict[str, Any]:
    brief = BriefIntelligenceService().get_brief(brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    return brief


@router.post("/briefs/{brief_id}/analyze")
async def analyze_brief(brief_id: str, refresh_sources: bool = True) -> Dict[str, Any]:
    try:
        return await BriefIntelligenceService().analyze_brief(brief_id, refresh_sources=refresh_sources)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Brief not found") from exc
    except Exception as exc:
        logger.error(f"Brief analysis failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/briefs/{brief_id}/recommendations")
async def get_brief_recommendations(brief_id: str) -> Dict[str, Any]:
    service = BriefIntelligenceService()
    brief = service.get_brief(brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    return {"brief_id": brief_id, "recommendations": service.get_recommendations(brief_id)}

