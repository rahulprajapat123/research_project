"""Daily intelligence and team email configuration APIs."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field, field_validator

from research_intelligence.daily_service import DailyIntelligenceService
from research_intelligence.store import get_store


router = APIRouter()


class TeamEmailSettingsRequest(BaseModel):
    team_email: str = Field(default="", description="Team distribution email")
    send_time: str = Field(default="08:00", description="HH:MM 24-hour local send time")
    timezone: str = Field(default="UTC")
    topics: List[str] = Field(default_factory=list)
    enabled: bool = False
    provider: str = "disabled"
    updated_by: str = "admin"

    @field_validator("team_email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if value and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
            raise ValueError("Invalid email address")
        return value

    @field_validator("send_time")
    @classmethod
    def validate_send_time(cls, value: str) -> str:
        if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", value):
            raise ValueError("send_time must use HH:MM 24-hour format")
        return value


@router.get("/intelligence/daily")
async def get_daily_intelligence(refresh: bool = False) -> Dict[str, Any]:
    service = DailyIntelligenceService()
    report = await service.generate_daily_report() if refresh else service.get_daily_report()
    if not report:
        report = await service.generate_daily_report()
    return report


@router.post("/intelligence/send-now")
async def send_daily_intelligence_now(topics: Optional[List[str]] = None) -> Dict[str, Any]:
    try:
        return await DailyIntelligenceService().send_now(topics=topics)
    except Exception as exc:
        logger.error(f"Send daily intelligence now failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/intelligence/email-history")
async def get_email_history(limit: int = 50) -> Dict[str, Any]:
    return {"logs": DailyIntelligenceService().email_history(limit=limit)}


@router.post("/settings/team-email")
async def save_team_email_settings(payload: TeamEmailSettingsRequest) -> Dict[str, Any]:
    record = get_store().save_team_email_settings(payload.model_dump())
    try:
        from ingestion.scheduler import get_scheduler

        get_scheduler().reschedule_daily_intelligence(record)
    except Exception as exc:
        logger.debug(f"Daily intelligence scheduler was not rescheduled: {exc}")
    return record


@router.get("/settings/team-email")
async def get_team_email_settings() -> Dict[str, Any]:
    return get_store().get_team_email_settings()

