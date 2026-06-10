"""Settings API endpoints backed by the intelligence store."""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional

from research_intelligence.store import get_store

router = APIRouter()


class TeamEmailSettings(BaseModel):
    """Team email settings model."""
    team_email: Optional[str] = ""
    send_time: str = "08:00"
    timezone: str = "UTC"
    provider: str = "disabled"
    enabled: bool = False
    topics: List[str] = Field(default_factory=list)


@router.get("/settings/team-email")
async def get_team_email_settings():
    """Get team email settings."""
    return get_store().get_team_email_settings()


@router.post("/settings/team-email")
async def save_team_email_settings(settings: TeamEmailSettings):
    """Save team email settings."""
    return get_store().save_team_email_settings(settings.model_dump())
