"""
Optional Apify-powered source integrations.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from loguru import logger

from config import get_settings

settings = get_settings()

try:
    from apify_client import ApifyClient
except ImportError:  # pragma: no cover - import guard for optional dependency
    ApifyClient = None


class ApifyScraperManager:
    """Manage optional Apify actor runs."""

    def __init__(self) -> None:
        if not settings.apify_api_token or ApifyClient is None:
            self.client = None
        else:
            self.client = ApifyClient(settings.apify_api_token)

    async def scrape_google_news(
        self,
        queries: List[str],
        max_results_per_query: int = 20,
    ) -> List[Dict[str, Any]]:
        if not self.client:
            logger.info("Apify not configured, skipping")
            return []

        all_results: List[Dict[str, Any]] = []
        for query in queries:
            try:
                items = await asyncio.to_thread(
                    self._run_google_news_actor,
                    query,
                    max_results_per_query,
                )
                all_results.extend(items)
            except Exception as exc:
                logger.warning(f"Apify Google News scrape failed for '{query}': {exc}")

        return all_results

    def _run_google_news_actor(self, query: str, max_results_per_query: int) -> List[Dict[str, Any]]:
        run = self.client.actor("apify/google-news-scraper").call(
            run_input={
                "searchQuery": query,
                "maxResults": max_results_per_query,
                "language": "en",
            },
            timeout_secs=settings.apify_timeout_secs,
        )
        results: List[Dict[str, Any]] = []
        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append(
                {
                    "title": item.get("title", ""),
                    "content": item.get("snippet", ""),
                    "authors": [item.get("source", "Unknown")],
                    "publication_date": (item.get("date") or "")[:10],
                    "url": item.get("link", ""),
                    "source_type": "apify_google_news",
                    "metadata": {
                        "source_name": item.get("source", ""),
                        "image_url": item.get("image", ""),
                        "query": query,
                    },
                }
            )
        return results
