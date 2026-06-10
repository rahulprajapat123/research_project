"""
Scheduled tasks for periodic multi-source metadata fetching.
"""
from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from config import get_settings
from ingestion.source_orchestrator import SourceOrchestrator

settings = get_settings()


class IngestionScheduler:
    """Schedule periodic fetch jobs for source metadata aggregation."""

    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()
        self.orchestrator = SourceOrchestrator()

    def start(self) -> None:
        if self.scheduler.running:
            return

        self.scheduler.add_job(
            self.fetch_news_sources,
            "interval",
            hours=settings.fetch_interval_hours,
            id="news_fetch",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self.fetch_research_sources,
            "cron",
            hour=settings.research_fetch_hour,
            id="research_fetch",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self.fetch_developer_sources,
            "cron",
            day_of_week="mon",
            hour=settings.developer_fetch_hour,
            id="developer_fetch",
            replace_existing=True,
        )
        self._add_daily_intelligence_job(self._load_daily_email_settings())
        self.scheduler.start()
        logger.info("Multi-source scheduler started")

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Multi-source scheduler stopped")

    async def fetch_news_sources(self) -> None:
        await self._run_job(
            job_name="news",
            keywords=settings.news_keywords,
            sources=["gnews", "newsapi", "rss", "google_news", "hackernews"],
        )

    async def fetch_research_sources(self) -> None:
        """Fetch research papers based on configured topics (domain-agnostic)."""
        # Use research_topics from config - works for ANY domain!
        # E.g., Healthcare: ["clinical trials", "patient outcomes", "EHR systems"]
        # E.g., Finance: ["risk modeling", "portfolio optimization", "fraud detection"]
        # E.g., Social: ["sentiment analysis", "social media monitoring", "NLP"]
        
        # Load topics from environment variable if set, otherwise use defaults
        import os
        env_topics = os.getenv("RESEARCH_TOPICS")
        if env_topics:
            keywords = [t.strip() for t in env_topics.split(",") if t.strip()]
            logger.info(f"Using research topics from env: {keywords[:3]}...")
        else:
            # Default RAG-focused topics if not configured
            keywords = [
                "retrieval augmented generation",
                "vector search",
                "semantic search",
                "embedding models",
                "dense retrieval",
                "RAG"
            ]
            logger.info(f"Using default research topics: {keywords[:3]}...")
        
        await self._run_job(
            job_name="research",
            keywords=keywords,
            sources=["arxiv", "semantic_scholar", "openalex", "exa"],
        )

    async def fetch_developer_sources(self) -> None:
        await self._run_job(
            job_name="developer",
            keywords=settings.news_keywords,
            sources=["github", "hackernews", "rss"],
        )

    async def send_daily_intelligence(self) -> None:
        try:
            from research_intelligence.daily_service import DailyIntelligenceService
            from research_intelligence.store import get_store

            email_settings = get_store().get_team_email_settings()
            if not email_settings.get("enabled") or not email_settings.get("team_email"):
                logger.info("Daily intelligence email skipped because it is disabled or missing a team email")
                return
            result = await DailyIntelligenceService().send_now(topics=email_settings.get("topics"))
            logger.info(f"Daily intelligence email job completed: {result['email_log']['status']}")
        except Exception as exc:
            logger.error(f"Daily intelligence email job failed: {exc}", exc_info=True)

    def reschedule_daily_intelligence(self, email_settings: dict) -> None:
        try:
            self.scheduler.remove_job("daily_intelligence_email")
        except Exception:
            pass
        self._add_daily_intelligence_job(email_settings)

    def _add_daily_intelligence_job(self, email_settings: dict) -> None:
        if not email_settings.get("enabled"):
            return
        send_time = str(email_settings.get("send_time") or "08:00")
        try:
            hour_text, minute_text = send_time.split(":", 1)
            hour = int(hour_text)
            minute = int(minute_text)
        except Exception:
            hour = settings.daily_intelligence_send_hour
            minute = settings.daily_intelligence_send_minute

        self.scheduler.add_job(
            self.send_daily_intelligence,
            "cron",
            hour=hour,
            minute=minute,
            timezone=email_settings.get("timezone") or settings.daily_intelligence_timezone,
            id="daily_intelligence_email",
            replace_existing=True,
        )

    def _load_daily_email_settings(self) -> dict:
        try:
            from research_intelligence.store import get_store

            record = get_store().get_team_email_settings()
            if record:
                return record
        except Exception as exc:
            logger.warning(f"Could not load saved daily email settings: {exc}")
        return {
            "enabled": settings.daily_intelligence_enabled,
            "send_time": f"{settings.daily_intelligence_send_hour:02d}:{settings.daily_intelligence_send_minute:02d}",
            "timezone": settings.daily_intelligence_timezone,
        }

    async def _run_job(self, job_name: str, keywords: list[str], sources: list[str]) -> None:
        try:
            result = await self.orchestrator.fetch_and_store(
                keywords=keywords,
                enable_apify=False,
                sources=sources,
            )
            logger.info(
                f"Scheduled {job_name} fetch completed: {result['items_fetched']} documents, "
                f"{result['items_new']} new rows"
            )
        except Exception as exc:
            logger.error(f"Scheduled {job_name} fetch failed: {exc}", exc_info=True)


_scheduler_instance: IngestionScheduler | None = None


def get_scheduler() -> IngestionScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = IngestionScheduler()
    return _scheduler_instance
