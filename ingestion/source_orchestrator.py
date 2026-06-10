"""
Orchestrates multi-source fetching, normalization, deduplication, and persistence.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional
from urllib.parse import urlparse

from loguru import logger
from sqlalchemy import text

from config import get_settings
from ingestion.source_classifier import classify_source_tier
from ingestion.sources.apify_scrapers import ApifyScraperManager
from ingestion.sources.developer_sources import GitHubFetcher, HackerNewsFetcher, GitHubAwesomeListsFetcher
from ingestion.sources.news_sources import (
    GNewsFetcher,
    GoogleNewsFetcher,
    NewsAPIFetcher,
    RSSFeedFetcher,
    MediaCloudFetcher,
    GDELTFetcher,
    GuardianAPIFetcher,
    NYTimesAPIFetcher,
    ExaFetcher,
)
from ingestion.sources.research_sources import (
    ArxivFetcher,
    OpenAlexFetcher,
    SemanticScholarFetcher,
    HuggingFacePapersFetcher,
    PapersWithCodeFetcher,
    AminerFetcher,
)

settings = get_settings()

SourceTask = Callable[[List[str]], Awaitable[List[Dict[str, Any]]]]
SOURCE_TIMEOUT_SECONDS = 55

KNOWN_SOURCES = {
    "arxiv",
    "semantic_scholar",
    "openalex",
    "huggingface_papers",
    "huggingface_datasets",
    "papers_with_code",
    "aminer",
    "gnews",
    "newsapi",
    "rss",
    "google_news",
    "mediacloud",
    "gdelt",
    "guardian",
    "nytimes",
    "exa",
    "github",
    "github_awesome_lists",
    "hackernews",
    "apify_google_news",
}


class SourceOrchestrator:
    """Coordinates fetching from all configured sources."""

    def __init__(self) -> None:
        self.arxiv = ArxivFetcher()
        self.semantic_scholar = SemanticScholarFetcher()
        self.openalex = OpenAlexFetcher()
        self.huggingface_papers = HuggingFacePapersFetcher()
        self.papers_with_code = PapersWithCodeFetcher()
        self.aminer = AminerFetcher()
        self.gnews = GNewsFetcher()
        self.newsapi = NewsAPIFetcher()
        self.rss = RSSFeedFetcher()
        self.google_news = GoogleNewsFetcher()
        self.mediacloud = MediaCloudFetcher()
        self.gdelt = GDELTFetcher()
        self.guardian = GuardianAPIFetcher()
        self.nytimes = NYTimesAPIFetcher()
        self.exa = ExaFetcher()
        self.github = GitHubFetcher()
        self.github_awesome_lists = GitHubAwesomeListsFetcher()
        self.hackernews = HackerNewsFetcher()
        self.apify = ApifyScraperManager()
        self.last_fetch_details: List[Dict[str, Any]] = []

    async def fetch_all_sources(
        self,
        keywords: Optional[List[str]] = None,
        enable_apify: bool = False,
        sources: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        if keywords is None:
            keywords = settings.news_keywords

        source_ids = self._resolve_sources(enable_apify=enable_apify, requested_sources=sources)
        source_tasks = self._build_source_tasks(source_ids)
        self.last_fetch_details = []
        results = await asyncio.gather(
            *(self._run_source_task(source_id, task, keywords) for source_id, task in source_tasks.items()),
            return_exceptions=True,
        )

        all_documents: List[Dict[str, Any]] = []
        successful_sources = 0
        failed_sources = 0
        for result in results:
            if isinstance(result, Exception):
                source_id = "unknown"
                logger.warning(f"Source '{source_id}' fetch failed: {type(result).__name__}: {result}")
                self.last_fetch_details.append(
                    {
                        "source_id": source_id,
                        "status": "failed",
                        "items": 0,
                        "error": str(result),
                    }
                )
                failed_sources += 1
                continue
            if isinstance(result, dict):
                detail = result.get("detail", {})
                self.last_fetch_details.append(detail)
                documents = result.get("documents", [])
                all_documents.extend(documents)
                if detail.get("status") in {"failed"}:
                    failed_sources += 1
                elif detail.get("items", 0) > 0:
                    successful_sources += 1
                else:
                    logger.info(
                        f"Source '{detail.get('source_id')}' returned no items"
                        + (f": {detail.get('error')}" if detail.get("error") else "")
                    )
            elif isinstance(result, list):
                all_documents.extend(result)
                successful_sources += 1
        
        if failed_sources > 0:
            logger.warning(f"Source fetch summary: {successful_sources} successful, {failed_sources} failed")

        normalized = self._normalize_all(all_documents)
        deduplicated = self._deduplicate(normalized)
        logger.info(f"Fetched {len(deduplicated)} unique documents from {len(source_tasks)} sources")
        return deduplicated

    async def fetch_and_store(
        self,
        keywords: Optional[List[str]] = None,
        enable_apify: bool = False,
        sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        started = time.perf_counter()
        documents = await self.fetch_all_sources(keywords=keywords, enable_apify=enable_apify, sources=sources)
        persistence = self.persist_documents(documents=documents, keywords=keywords or settings.news_keywords)
        duration = round(time.perf_counter() - started, 3)

        return {
            "documents": documents,
            "items_fetched": len(documents),
            "items_new": persistence["items_new"],
            "items_updated": persistence["items_updated"],
            "fetch_duration_seconds": duration,
            "sources_used": sorted({doc["source_type"] for doc in documents}),
            "source_details": self.last_fetch_details,
        }

    def persist_documents(self, documents: List[Dict[str, Any]], keywords: List[str]) -> Dict[str, int]:
        """
        Persist documents to database or local fallback if database unavailable.
        """
        try:
            return self._persist_to_database(documents, keywords)
        except Exception as exc:
            logger.warning(f"Database persistence failed, using local fallback: {exc}")
            return self._persist_to_local_file(documents, keywords=keywords)
    
    def _persist_to_database(self, documents: List[Dict[str, Any]], keywords: List[str]) -> Dict[str, int]:
        """Persist documents to PostgreSQL database."""
        from database.connection import get_db_context

        items_new = 0
        items_updated = 0
        per_source_stats: Dict[str, Dict[str, int]] = {}

        with get_db_context() as db:
            for doc in documents:
                if not doc.get("url"):
                    continue
                parsed = urlparse(doc.get("url") or "")
                publication_date = self._parse_publication_date(doc.get("publication_date"))
                metadata_json = json.dumps(doc.get("metadata", {}))

                result = db.execute(
                    text(
                        """
                        INSERT INTO sources (
                            url, title, authors, publication_date, source_type, domain,
                            tier, credibility_score, citation_count, author_h_index,
                            metadata, ingestion_status
                        ) VALUES (
                            :url, :title, :authors, :publication_date, :source_type, :domain,
                            :tier, :credibility_score, :citation_count, :author_h_index,
                            CAST(:metadata AS jsonb), 'pending'
                        )
                        ON CONFLICT (url) DO UPDATE SET
                            title = EXCLUDED.title,
                            authors = EXCLUDED.authors,
                            publication_date = COALESCE(EXCLUDED.publication_date, sources.publication_date),
                            source_type = EXCLUDED.source_type,
                            domain = EXCLUDED.domain,
                            tier = EXCLUDED.tier,
                            credibility_score = EXCLUDED.credibility_score,
                            citation_count = GREATEST(sources.citation_count, EXCLUDED.citation_count),
                            author_h_index = COALESCE(EXCLUDED.author_h_index, sources.author_h_index),
                            metadata = sources.metadata || EXCLUDED.metadata,
                            ingestion_status = CASE
                                WHEN sources.ingestion_status = 'completed' THEN sources.ingestion_status
                                ELSE 'pending'
                            END,
                            updated_at = NOW()
                        RETURNING (xmax = 0) AS inserted
                        """
                    ),
                    {
                        "url": doc.get("url"),
                        "title": doc.get("title"),
                        "authors": doc.get("authors", []),
                        "publication_date": publication_date,
                        "source_type": doc.get("source_type"),
                        "domain": parsed.netloc.lower(),
                        "tier": doc.get("tier"),
                        "credibility_score": doc.get("credibility_score", 0),
                        "citation_count": doc.get("metadata", {}).get("citation_count", 0),
                        "author_h_index": doc.get("metadata", {}).get("author_h_index"),
                        "metadata": metadata_json,
                    },
                ).scalar()

                source_stats = per_source_stats.setdefault(
                    doc.get("source_type", "unknown"),
                    {"new": 0, "updated": 0},
                )
                if result:
                    items_new += 1
                    source_stats["new"] += 1
                else:
                    items_updated += 1
                    source_stats["updated"] += 1

            self._record_fetch_logs(db, documents, keywords, per_source_stats)
            db.commit()

        return {"items_new": items_new, "items_updated": items_updated}

    def get_fetch_stats(self, limit: int = 20) -> Dict[str, Any]:
        """Get fetch statistics from database or return empty if unavailable."""
        try:
            from database.connection import get_db_context

            with get_db_context() as db:
                recent_rows = db.execute(
                    text(
                        """
                        SELECT source_type, fetch_timestamp, items_fetched, items_new,
                               items_duplicate, fetch_duration_seconds, status, error_message
                        FROM fetch_logs
                        ORDER BY fetch_timestamp DESC
                        LIMIT :limit
                        """
                    ),
                    {"limit": limit},
                ).mappings().all()

                aggregate_rows = db.execute(
                    text(
                        """
                        SELECT source_type,
                               COUNT(*) AS runs,
                               SUM(items_fetched) AS total_fetched,
                               SUM(items_new) AS total_new,
                               SUM(items_duplicate) AS total_duplicates,
                               MAX(fetch_timestamp) AS last_fetch,
                               MAX(status) FILTER (WHERE fetch_timestamp IS NOT NULL) AS latest_status
                        FROM fetch_logs
                        GROUP BY source_type
                        ORDER BY source_type
                        """
                    )
                ).mappings().all()

            return {
                "recent_runs": [dict(row) for row in recent_rows],
                "by_source": [dict(row) for row in aggregate_rows],
            }
        except Exception as exc:
            logger.debug(f"Database fetch stats unavailable: {exc}")
            return self._get_local_fetch_stats(limit=limit)
    
    def _persist_to_local_file(self, documents: List[Dict[str, Any]], keywords: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Fallback persistence to local JSON file when database is unavailable.
        """
        import os
        from pathlib import Path
        
        storage_path = Path(settings.storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)
        sources_file = storage_path / "fetched_sources.json"
        
        # Load existing sources
        existing_sources = {}
        existing_logs: List[Dict[str, Any]] = []
        if sources_file.exists():
            try:
                with open(sources_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    existing_sources = {
                        doc.get("url"): doc
                        for doc in data.get("sources", [])
                        if isinstance(doc, dict) and doc.get("url")
                    }
                    existing_logs = data.get("fetch_logs", []) if isinstance(data.get("fetch_logs"), list) else []
            except Exception as exc:
                logger.warning(f"Could not load existing sources file: {exc}")
        
        # Merge new documents
        items_new = 0
        items_updated = 0
        new_by_source: Dict[str, int] = {}
        updated_by_source: Dict[str, int] = {}
        for doc in documents:
            url = doc.get("url")
            if not url:
                continue
            source_type = doc.get("source_type") or "unknown"
            
            if url in existing_sources:
                items_updated += 1
                updated_by_source[source_type] = updated_by_source.get(source_type, 0) + 1
                # Update existing document
                existing_sources[url].update({
                    "title": doc.get("title"),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
            else:
                items_new += 1
                new_by_source[source_type] = new_by_source.get(source_type, 0) + 1
                # Add new document
                existing_sources[url] = {
                    **doc,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }

        now = datetime.now(timezone.utc).isoformat()
        counts_by_source: Dict[str, int] = {}
        for doc in documents:
            source_type = doc.get("source_type") or "unknown"
            counts_by_source[source_type] = counts_by_source.get(source_type, 0) + 1
        for source_type, count in counts_by_source.items():
            existing_logs.append(
                {
                    "source_type": source_type,
                    "fetch_timestamp": now,
                    "items_fetched": count,
                    "items_new": new_by_source.get(source_type, 0),
                    "items_duplicate": updated_by_source.get(source_type, 0),
                    "fetch_duration_seconds": 0,
                    "status": "success",
                    "error_message": None,
                    "keywords": keywords or settings.news_keywords,
                }
            )
        
        # Save back to file
        try:
            with open(sources_file, "w", encoding="utf-8") as f:
                json.dump({
                    "sources": list(existing_sources.values()),
                    "fetch_logs": existing_logs[-200:],
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "total_count": len(existing_sources),
                }, f, indent=2, default=str)
            logger.info(f"Persisted {items_new} new and {items_updated} updated documents to local file")
        except Exception as exc:
            logger.error(f"Failed to save sources to local file: {exc}")
        
        return {"items_new": items_new, "items_updated": items_updated}

    def _get_local_fetch_stats(self, limit: int = 20) -> Dict[str, Any]:
        sources_file = Path(settings.storage_path) / "fetched_sources.json"
        if not sources_file.exists():
            return {"recent_runs": [], "by_source": []}
        try:
            with open(sources_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            logger.warning(f"Could not read local fetch stats: {exc}")
            return {"recent_runs": [], "by_source": []}
        logs = data.get("fetch_logs", [])
        if not isinstance(logs, list):
            return {"recent_runs": [], "by_source": []}
        recent_runs = sorted(logs, key=lambda row: row.get("fetch_timestamp") or "", reverse=True)[:limit]
        grouped: Dict[str, Dict[str, Any]] = {}
        for log in logs:
            source_type = log.get("source_type") or "unknown"
            row = grouped.setdefault(
                source_type,
                {
                    "source_type": source_type,
                    "runs": 0,
                    "total_fetched": 0,
                    "total_new": 0,
                    "total_duplicates": 0,
                    "last_fetch": None,
                    "latest_status": "unknown",
                },
            )
            row["runs"] += 1
            row["total_fetched"] += int(log.get("items_fetched") or 0)
            row["total_new"] += int(log.get("items_new") or 0)
            row["total_duplicates"] += int(log.get("items_duplicate") or 0)
            timestamp = log.get("fetch_timestamp")
            if timestamp and (not row["last_fetch"] or str(timestamp) > str(row["last_fetch"])):
                row["last_fetch"] = timestamp
                row["latest_status"] = log.get("status") or row["latest_status"]
        return {"recent_runs": recent_runs, "by_source": sorted(grouped.values(), key=lambda row: row["source_type"])}

    async def _run_source_task(
        self,
        source_id: str,
        task: SourceTask,
        keywords: List[str],
    ) -> Dict[str, Any]:
        started = time.perf_counter()
        try:
            documents = await asyncio.wait_for(task(keywords), timeout=SOURCE_TIMEOUT_SECONDS)
            credential_message = self._credential_message(source_id)
            status = "ok" if documents else ("skipped" if credential_message else "empty")
            return {
                "documents": documents,
                "detail": {
                    "source_id": source_id,
                    "status": status,
                    "items": len(documents),
                    "duration_seconds": round(time.perf_counter() - started, 3),
                    "error": credential_message if status == "skipped" else None,
                },
            }
        except Exception as exc:
            logger.error(f"Source task failed for {source_id}: {exc}")
            error_message = (
                f"Timed out after {SOURCE_TIMEOUT_SECONDS} seconds"
                if isinstance(exc, asyncio.TimeoutError)
                else str(exc)
            )
            return {
                "documents": [],
                "detail": {
                    "source_id": source_id,
                    "status": "failed",
                    "items": 0,
                    "duration_seconds": round(time.perf_counter() - started, 3),
                    "error": error_message,
                },
            }

    def _resolve_sources(self, enable_apify: bool, requested_sources: Optional[List[str]]) -> List[str]:
        source_ids = set(requested_sources or (KNOWN_SOURCES - {"apify_google_news"}))
        unknown = sorted(source_id for source_id in source_ids if source_id not in KNOWN_SOURCES)
        if unknown:
            raise ValueError(f"Unsupported source ids: {', '.join(unknown)}")
        if not enable_apify:
            source_ids.discard("apify_google_news")
        return sorted(source_ids)

    def _build_source_tasks(self, source_ids: List[str]) -> Dict[str, SourceTask]:
        return {
            source_id: task
            for source_id, task in {
                "arxiv": self._fetch_arxiv,
                "semantic_scholar": self._fetch_semantic_scholar,
                "openalex": self._fetch_openalex,
                "huggingface_papers": self._fetch_huggingface_papers,
                "huggingface_datasets": self._fetch_huggingface_datasets,
                "papers_with_code": self._fetch_papers_with_code,
                "aminer": self._fetch_aminer,
                "gnews": self._fetch_gnews,
                "newsapi": self._fetch_newsapi,
                "rss": self._fetch_rss,
                "google_news": self._fetch_google_news,
                "mediacloud": self._fetch_mediacloud,
                "gdelt": self._fetch_gdelt,
                "guardian": self._fetch_guardian,
                "nytimes": self._fetch_nytimes,
                "exa": self._fetch_exa,
                "github": self._fetch_github,
                "github_awesome_lists": self._fetch_github_awesome_lists,
                "hackernews": self._fetch_hackernews,
                "apify_google_news": self._fetch_apify_google_news,
            }.items()
            if source_id in source_ids
        }

    async def _fetch_arxiv(self, keywords: List[str]) -> List[Dict[str, Any]]:
        return await self.arxiv.search(keywords=keywords, max_results=settings.max_papers_per_source)

    async def _fetch_semantic_scholar(self, keywords: List[str]) -> List[Dict[str, Any]]:
        if not settings.semantic_scholar_api_key:
            logger.info("Semantic Scholar API key not configured, skipping")
            return []
        results: List[Dict[str, Any]] = []
        for keyword in keywords[:3]:
            try:
                results.extend(await self.semantic_scholar.search(keyword, limit=20))
            except Exception as exc:
                logger.warning(f"Semantic Scholar search failed for '{keyword}': {exc}")
                continue
        return results

    async def _fetch_openalex(self, keywords: List[str]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for keyword in keywords[:3]:
            try:
                results.extend(await self.openalex.search(keyword, limit=20))
            except Exception as exc:
                logger.warning(f"OpenAlex search failed for '{keyword}': {exc}")
                continue
        return results

    async def _fetch_gnews(self, keywords: List[str]) -> List[Dict[str, Any]]:
        return await self.gnews.search(" OR ".join(keywords[:3]), max_articles=settings.max_news_articles_per_source)

    async def _fetch_newsapi(self, keywords: List[str]) -> List[Dict[str, Any]]:
        return await self.newsapi.search(" OR ".join(keywords[:3]), max_articles=settings.max_news_articles_per_source)

    async def _fetch_rss(self, _: List[str]) -> List[Dict[str, Any]]:
        return await self.rss.fetch_all_feeds(settings.rss_feeds)

    async def _fetch_google_news(self, keywords: List[str]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for keyword in keywords[:3]:
            try:
                results.extend(await self.google_news.search(keyword))
            except Exception as exc:
                logger.warning(f"Google News search failed for '{keyword}': {exc}")
                continue
        return results

    async def _fetch_github(self, keywords: List[str]) -> List[Dict[str, Any]]:
        topic_candidates = [
            self._github_topic_slug(keyword)
            for keyword in keywords
            if self._github_topic_slug(keyword)
        ]
        topics = topic_candidates[:3] or settings.github_topics[:3]
        return await self.github.search_repositories(
            topics=topics,
            max_results=min(settings.max_github_repos, 12),
            include_readme=False,
        )

    async def _fetch_hackernews(self, keywords: List[str]) -> List[Dict[str, Any]]:
        return await self.hackernews.search(keywords=keywords[:5], days_back=settings.news_lookback_days)

    async def _fetch_apify_google_news(self, keywords: List[str]) -> List[Dict[str, Any]]:
        return await self.apify.scrape_google_news(keywords[:3])

    async def _fetch_huggingface_papers(self, _: List[str]) -> List[Dict[str, Any]]:
        """Fetch daily curated papers from Hugging Face."""
        return await self.huggingface_papers.fetch_daily_papers(limit=settings.max_papers_per_source)

    async def _fetch_huggingface_datasets(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Search Hugging Face datasets for RAG-related content."""
        results: List[Dict[str, Any]] = []
        for keyword in keywords[:3]:
            results.extend(await self.huggingface_papers.search_datasets(keyword, limit=10))
        return results

    async def _fetch_papers_with_code(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Fetch papers from Papers with Code."""
        results: List[Dict[str, Any]] = []
        # First get trending papers
        results.extend(await self.papers_with_code.get_trending_papers(limit=20))
        # Then search for specific keywords
        for keyword in keywords[:2]:
            results.extend(await self.papers_with_code.search_papers(query=keyword, items_per_page=15))
        return results

    async def _fetch_aminer(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Fetch papers from Aminer."""
        results: List[Dict[str, Any]] = []
        for keyword in keywords[:3]:
            results.extend(await self.aminer.search_papers(keyword, size=20))
        return results

    async def _fetch_github_awesome_lists(self, _: List[str]) -> List[Dict[str, Any]]:
        """Fetch curated awesome lists from GitHub."""
        return await self.github_awesome_lists.fetch_awesome_lists()

    async def _fetch_mediacloud(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Fetch articles from Media Cloud research platform."""
        return await self.mediacloud.search(" OR ".join(keywords[:3]), max_articles=settings.max_news_articles_per_source)

    async def _fetch_gdelt(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Fetch articles from GDELT global news database."""
        results: List[Dict[str, Any]] = []
        for keyword in keywords[:3]:
            results.extend(await self.gdelt.search(keyword, max_records=50))
        return results

    async def _fetch_guardian(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Fetch articles from The Guardian API."""
        return await self.guardian.search(" OR ".join(keywords[:3]), page_size=50)

    async def _fetch_nytimes(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Fetch articles from The New York Times API."""
        results: List[Dict[str, Any]] = []
        for keyword in keywords[:3]:
            results.extend(await self.nytimes.search(keyword))
        return results
    
    async def _fetch_exa(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Fetch high-quality research content from Exa.ai semantic search."""
        results: List[Dict[str, Any]] = []
        for keyword in keywords[:3]:
            results.extend(await self.exa.search(keyword, num_results=10))
        return results

    def _normalize_all(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for doc in documents:
            title = (doc.get("title") or "").strip()
            title_key = self._normalize_title(title)
            url = self._canonicalize_url(doc.get("url", ""))
            if not url and title_key:
                url = f"urn:{doc.get('source_type', 'unknown')}:{hashlib.md5(title_key.encode('utf-8')).hexdigest()}"
            content = (doc.get("content") or doc.get("abstract") or "").strip()
            metadata = dict(doc.get("metadata") or {})
            tier, credibility_score = classify_source_tier(
                url,
                citation_count=metadata.get("citation_count", 0),
                author_h_index=metadata.get("author_h_index"),
            )
            dedupe_key = url or title_key

            normalized.append(
                {
                    "url": url,
                    "title": title,
                    "content": content,
                    "authors": [author for author in doc.get("authors", []) if author],
                    "publication_date": doc.get("publication_date", ""),
                    "source_type": doc.get("source_type", "unknown"),
                    "tier": tier,
                    "credibility_score": credibility_score,
                    "metadata": metadata,
                    "fetched_at": datetime.utcnow().isoformat(),
                    "dedupe_key": dedupe_key,
                    "dedupe_hash": hashlib.md5(dedupe_key.encode("utf-8")).hexdigest() if dedupe_key else "",
                }
            )
        return normalized

    def _deduplicate(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen: set[str] = set()
        unique_docs: List[Dict[str, Any]] = []
        for doc in documents:
            dedupe_hash = doc.get("dedupe_hash", "")
            if not dedupe_hash or dedupe_hash in seen:
                continue
            seen.add(dedupe_hash)
            unique_docs.append(doc)
        return unique_docs

    def _record_fetch_logs(
        self,
        db: Any,
        documents: List[Dict[str, Any]],
        keywords: List[str],
        per_source_stats: Dict[str, Dict[str, int]],
    ) -> None:
        counts_by_source: Dict[str, int] = {}
        for doc in documents:
            counts_by_source[doc["source_type"]] = counts_by_source.get(doc["source_type"], 0) + 1

        for source_type, item_count in counts_by_source.items():
            inserted_count = per_source_stats.get(source_type, {}).get("new", 0)
            updated_count = per_source_stats.get(source_type, {}).get("updated", 0)
            db.execute(
                text(
                    """
                    INSERT INTO fetch_logs (
                        source_type, items_fetched, items_new, items_duplicate,
                        fetch_duration_seconds, status, metadata, keywords
                    ) VALUES (
                        :source_type, :items_fetched, :items_new, :items_duplicate,
                        0, 'success', CAST(:metadata AS jsonb), :keywords
                    )
                    """
                ),
                {
                    "source_type": source_type,
                    "items_fetched": item_count,
                    "items_new": inserted_count,
                    "items_duplicate": updated_count,
                    "metadata": json.dumps({"source_type": source_type}),
                    "keywords": keywords,
                },
            )

    @staticmethod
    def _canonicalize_url(url: str) -> str:
        return (url or "").strip()

    @staticmethod
    def _normalize_title(title: str) -> str:
        return " ".join((title or "").lower().split())

    @staticmethod
    def _parse_publication_date(value: Any) -> Optional[date]:
        if not value:
            return None
        if isinstance(value, date):
            return value
        text_value = str(value).strip()
        for candidate in (text_value, text_value[:10], text_value[:7], text_value[:4]):
            try:
                if len(candidate) == 10:
                    return datetime.strptime(candidate, "%Y-%m-%d").date()
                if len(candidate) == 7:
                    return datetime.strptime(candidate, "%Y-%m").date()
                if len(candidate) == 4:
                    return datetime.strptime(candidate, "%Y").date()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text_value.replace("Z", "+00:00")).date()
        except ValueError:
            return None

    @staticmethod
    def _github_topic_slug(value: str) -> str:
        slug = "-".join(str(value or "").lower().split())
        slug = "".join(char for char in slug if char.isalnum() or char == "-").strip("-")
        if len(slug) < 2 or len(slug) > 50:
            return ""
        return slug

    @staticmethod
    def _credential_message(source_id: str) -> Optional[str]:
        credential_map = {
            "semantic_scholar": ("SEMANTIC_SCHOLAR_API_KEY", settings.semantic_scholar_api_key),
            "gnews": ("GNEWS_API_KEY", settings.gnews_api_key),
            "newsapi": ("NEWSAPI_KEY", settings.newsapi_key),
            "mediacloud": ("MEDIACLOUD_API_KEY", settings.mediacloud_api_key),
            "guardian": ("GUARDIAN_API_KEY", settings.guardian_api_key),
            "nytimes": ("NYTIMES_API_KEY", settings.nytimes_api_key),
            "exa": ("EXA_API_KEY", settings.exa_api_key),
            "aminer": ("AMINER_API_KEY", settings.aminer_api_key),
            "apify_google_news": ("APIFY_API_TOKEN", settings.apify_api_token),
        }
        item = credential_map.get(source_id)
        if item and not item[1]:
            return f"{item[0]} is not configured"
        return None
