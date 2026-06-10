"""Persistence helpers with Postgres-first and local JSON fallback behavior."""
from __future__ import annotations

import json
import re
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from loguru import logger
from sqlalchemy import text

from config import get_settings


settings = get_settings()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class IntelligenceStore:
    """Store intelligence objects in Postgres when available, otherwise JSON."""

    def __init__(self, local_path: Optional[Path] = None, use_postgres: bool = True) -> None:
        base_path = Path(settings.storage_path)
        self.local_path = local_path or base_path / "intelligence_store.json"
        self.local_sources_path = (
            base_path / "fetched_sources.json"
            if local_path is None
            else self.local_path.with_name(f"{self.local_path.stem}_sources.json")
        )
        self.use_postgres = use_postgres
        self._lock = threading.Lock()
        self._ensure_local_store()

    def create_brief(
        self,
        file_name: str,
        file_type: str,
        file_size_bytes: int,
        content_text: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        brief = {
            "id": str(uuid4()),
            "file_name": file_name,
            "file_type": file_type,
            "file_size_bytes": file_size_bytes,
            "content_text": content_text,
            "parsed_summary": "",
            "metadata": metadata,
            "processing_status": "parsed",
            "processing_error": None,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }

        if self._with_db(lambda db: self._db_insert_brief(db, brief)):
            return brief
        self._local_upsert("briefs", brief)
        return brief

    def get_brief(self, brief_id: str) -> Optional[Dict[str, Any]]:
        result = self._with_db(lambda db: self._db_get_brief(db, brief_id))
        if result is not None:
            return result
        return self._local_get("briefs", brief_id)

    def update_brief(self, brief_id: str, **updates: Any) -> None:
        updates["updated_at"] = utc_now_iso()
        if self._with_db(lambda db: self._db_update_brief(db, brief_id, updates)):
            return
        self._local_update("briefs", brief_id, updates)

    def save_brief_topics(self, brief_id: str, topics: List[Dict[str, Any]]) -> None:
        records = []
        for topic in topics:
            records.append(
                {
                    "id": str(uuid4()),
                    "brief_id": brief_id,
                    "topic": topic.get("topic") or topic.get("name") or str(topic),
                    "category": topic.get("category", "technical"),
                    "confidence_score": float(topic.get("confidence_score", 0.75)),
                    "created_at": utc_now_iso(),
                    "updated_at": utc_now_iso(),
                }
            )
        if self._with_db(lambda db: self._db_save_topics(db, brief_id, records)):
            return
        self._local_replace_by("brief_topics", "brief_id", brief_id, records)

    def get_brief_topics(self, brief_id: str) -> List[Dict[str, Any]]:
        result = self._with_db(lambda db: self._db_get_topics(db, brief_id))
        if result is not None:
            return result
        data = self._read_local()
        return [item for item in data["brief_topics"] if item.get("brief_id") == brief_id]

    def save_recommendations(self, brief_id: str, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        records = []
        for recommendation in recommendations:
            record = {
                "id": recommendation.get("id") or str(uuid4()),
                "brief_id": brief_id,
                "technology_name": recommendation.get("technology_name"),
                "category": recommendation.get("category", "technology"),
                "summary": recommendation.get("description", ""),
                "recommendation": recommendation.get("why_relevant", ""),
                "description": recommendation.get("description", ""),
                "why_relevant": recommendation.get("why_relevant", ""),
                "confidence_score": float(recommendation.get("confidence_score", 0)),
                "implementation_difficulty": recommendation.get("implementation_difficulty", "Medium"),
                "final_score": float(recommendation.get("confidence_score", 0)),
                "alternatives": recommendation.get("alternatives", []),
                "risks_tradeoffs": recommendation.get("risks_tradeoffs", []),
                "suggested_architecture": recommendation.get("suggested_architecture", ""),
                "next_steps": recommendation.get("next_steps", []),
                "citations": recommendation.get("citations", []),
                "scoring_breakdown": recommendation.get("scoring_breakdown", {}),
                "source_count": recommendation.get("source_count", 0),
                "evidence_score": recommendation.get("evidence_score", recommendation.get("confidence_score", 0)),
                "recency_score": recommendation.get("recency_score", 0),
                "adoption_signal": recommendation.get("adoption_signal", 0),
                "radar_stage": recommendation.get("radar_stage", "Assess"),
                "status": "active",
                "created_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
            }
            records.append(record)

        if self._with_db(lambda db: self._db_save_recommendations(db, brief_id, records)):
            return records
        self._local_replace_by("brief_recommendations", "brief_id", brief_id, records)
        return records

    def get_recommendations(self, brief_id: str) -> List[Dict[str, Any]]:
        result = self._with_db(lambda db: self._db_get_recommendations(db, brief_id))
        if result is not None:
            return result
        data = self._read_local()
        return [item for item in data["brief_recommendations"] if item.get("brief_id") == brief_id]

    def get_recommendation(self, recommendation_id: str) -> Optional[Dict[str, Any]]:
        result = self._with_db(lambda db: self._db_get_recommendation(db, recommendation_id))
        if result is not None:
            return result
        return self._local_get("brief_recommendations", recommendation_id)

    def save_technology_radar(self, radar_items: List[Dict[str, Any]]) -> None:
        if self._with_db(lambda db: self._db_save_technology_radar(db, radar_items)):
            return
        self._local_replace_all("technologies", [{"id": item.get("id") or str(uuid4()), **item} for item in radar_items])

    def get_technology_radar(self) -> List[Dict[str, Any]]:
        result = self._with_db(lambda db: self._db_get_technology_radar(db))
        if result is not None:
            return result
        return self._read_local()["technologies"]

    def query_sources(self, query_terms: List[str], limit: int = 80) -> List[Dict[str, Any]]:
        result = self._with_db(lambda db: self._db_query_sources(db, query_terms, limit))
        if result is not None:
            return result
        terms = [str(term).lower() for term in query_terms if str(term).strip()]
        scored: List[Dict[str, Any]] = []
        for source in self._read_local_sources():
            haystack = _source_search_text(source)
            score = sum(1 for term in terms if term and term in haystack)
            if score <= 0 and terms:
                token_hits = len(_query_tokens(terms) & _query_tokens([haystack]))
                score = token_hits
            if score > 0 or not terms:
                document = _local_source_document(source)
                document["_local_match_score"] = score
                scored.append(document)
        scored.sort(
            key=lambda item: (
                item.get("_local_match_score", 0),
                item.get("credibility_score", 0),
                _date_sort_value(item.get("publication_date") or item.get("created_at")),
            ),
            reverse=True,
        )
        for item in scored:
            item.pop("_local_match_score", None)
        return scored[:limit]

    def get_research_feed(
        self,
        query: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        result = self._with_db(lambda db: self._db_research_feed(db, query, source_type, limit))
        if result is not None:
            return result
        query_lower = (query or "").lower().strip()
        items = []
        for source in self._read_local_sources():
            if source_type and source.get("source_type") != source_type:
                continue
            if query_lower and query_lower not in _source_search_text(source):
                continue
            items.append(_local_source_document(source))
        items.sort(key=lambda item: _date_sort_value(item.get("publication_date") or item.get("created_at")), reverse=True)
        return items[:limit]

    def save_daily_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        report = {
            "id": report.get("id") or str(uuid4()),
            "report_date": report.get("report_date") or date.today().isoformat(),
            "subject": report.get("subject", ""),
            "summary": report.get("summary", ""),
            "top_updates": report.get("top_updates", []),
            "worth_exploring": report.get("worth_exploring", []),
            "emerging_signals": report.get("emerging_signals", []),
            "ignore_for_now": report.get("ignore_for_now", []),
            "html_body": report.get("html_body", ""),
            "markdown_body": report.get("markdown_body", ""),
            "citations": report.get("citations", []),
            "source_status": report.get("source_status", []),
            "warnings": report.get("warnings", []),
            "processing_status": report.get("processing_status", "completed"),
            "created_at": report.get("created_at") or utc_now_iso(),
            "updated_at": utc_now_iso(),
        }
        if self._with_db(lambda db: self._db_save_daily_report(db, report)):
            return report
        self._local_upsert("daily_reports", report)
        return report

    def get_latest_daily_report(self) -> Optional[Dict[str, Any]]:
        result = self._with_db(lambda db: self._db_latest_daily_report(db))
        if result is not None:
            return result
        reports = sorted(self._read_local()["daily_reports"], key=lambda item: item.get("created_at", ""), reverse=True)
        return reports[0] if reports else None

    def list_daily_reports(self, limit: int = 20) -> List[Dict[str, Any]]:
        result = self._with_db(lambda db: self._db_list_daily_reports(db, limit))
        if result is not None:
            return result
        return sorted(self._read_local()["daily_reports"], key=lambda item: item.get("created_at", ""), reverse=True)[:limit]

    def save_email_log(self, log_record: Dict[str, Any]) -> Dict[str, Any]:
        record = {
            "id": log_record.get("id") or str(uuid4()),
            "report_id": log_record.get("report_id"),
            "recipient_email": log_record.get("recipient_email"),
            "provider": log_record.get("provider"),
            "subject": log_record.get("subject"),
            "status": log_record.get("status"),
            "error_message": log_record.get("error_message"),
            "sent_at": log_record.get("sent_at"),
            "created_at": log_record.get("created_at") or utc_now_iso(),
            "updated_at": utc_now_iso(),
        }
        if self._with_db(lambda db: self._db_save_email_log(db, record)):
            return record
        self._local_upsert("email_logs", record)
        return record

    def list_email_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        result = self._with_db(lambda db: self._db_list_email_logs(db, limit))
        if result is not None:
            return result
        return sorted(self._read_local()["email_logs"], key=lambda item: item.get("created_at", ""), reverse=True)[:limit]

    def get_team_email_settings(self) -> Dict[str, Any]:
        result = self._with_db(lambda db: self._db_get_team_email_settings(db))
        if result is not None:
            return result
        data = self._read_local()
        return data.get("team_email_settings") or _default_team_email_settings()

    def save_team_email_settings(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.get_team_email_settings()
        record = {
            **existing,
            **payload,
            "id": existing.get("id") or str(uuid4()),
            "updated_at": utc_now_iso(),
        }
        record.setdefault("created_at", utc_now_iso())
        if self._with_db(lambda db: self._db_save_team_email_settings(db, record)):
            return record
        data = self._read_local()
        data["team_email_settings"] = record
        self._write_local(data)
        return record

    def dashboard_overview(self) -> Dict[str, Any]:
        result = self._with_db(lambda db: self._db_dashboard_overview(db))
        if result is not None:
            return result
        data = self._read_local()
        local_sources = [_local_source_document(source) for source in self._read_local_sources()]
        fetch_logs = self._read_local_fetch_logs()
        latest_report = self.get_latest_daily_report()
        latest_email = self.list_email_logs(limit=1)
        news_types = {"gnews", "newsapi", "rss_feed", "google_news", "hackernews", "guardian", "nytimes", "gdelt", "mediacloud", "exa"}
        paper_types = {"arxiv", "openalex", "semantic_scholar", "papers_with_code", "huggingface_papers"}
        latest_papers = [item for item in local_sources if item.get("source_type") in paper_types][:5]
        latest_market_news = [item for item in local_sources if item.get("source_type") in news_types][:5]
        total_fetches = len(fetch_logs)
        successful_fetches = sum(1 for log in fetch_logs if log.get("status") == "success")
        return {
            "total_sources_monitored": len(local_sources),
            "active_sources": len({item.get("source_type") for item in local_sources if item.get("source_type")}),
            "items_ingested_today": sum(1 for item in local_sources if _is_today(item.get("created_at") or item.get("fetched_at"))),
            "items_ingested_this_week": sum(1 for item in local_sources if _is_this_week(item.get("created_at") or item.get("fetched_at"))),
            "latest_papers": latest_papers,
            "latest_tools": [],
            "latest_market_news": latest_market_news,
            "trending_technologies": data["technologies"][:8],
            "system_health": {
                "status": "operational" if local_sources or latest_report else "needs_setup",
                "note": "Using local JSON source store because Postgres is unavailable",
            },
            "ingestion_success_rate": round(successful_fetches / total_fetches, 3) if total_fetches else None,
            "email_delivery_status": latest_email[0] if latest_email else None,
            "latest_daily_report": latest_report,
        }

    def source_management(self) -> Dict[str, Any]:
        result = self._with_db(lambda db: self._db_source_management(db))
        if result is not None:
            return result
        local_sources = [_local_source_document(source) for source in self._read_local_sources()]
        fetch_logs = self._read_local_fetch_logs()
        source_rows: List[Dict[str, Any]] = []
        grouped: Dict[str, Dict[str, Any]] = {}
        for item in local_sources:
            source_type = item.get("source_type") or "unknown"
            row = grouped.setdefault(
                source_type,
                {
                    "source_type": source_type,
                    "last_fetch_time": None,
                    "fetch_count": 0,
                    "items_fetched": 0,
                    "latest_status": "success",
                    "last_error": None,
                },
            )
            row["items_fetched"] += 1
            timestamp = item.get("created_at") or item.get("fetched_at")
            if timestamp and (not row["last_fetch_time"] or str(timestamp) > str(row["last_fetch_time"])):
                row["last_fetch_time"] = timestamp
        for log in fetch_logs:
            source_type = log.get("source_type") or "unknown"
            row = grouped.setdefault(
                source_type,
                {
                    "source_type": source_type,
                    "last_fetch_time": None,
                    "fetch_count": 0,
                    "items_fetched": 0,
                    "latest_status": "unknown",
                    "last_error": None,
                },
            )
            row["fetch_count"] += 1
            if log.get("fetch_timestamp") and (
                not row["last_fetch_time"] or str(log.get("fetch_timestamp")) > str(row["last_fetch_time"])
            ):
                row["last_fetch_time"] = log.get("fetch_timestamp")
                row["latest_status"] = log.get("status") or row["latest_status"]
                row["last_error"] = log.get("error_message")
        source_rows = sorted(grouped.values(), key=lambda row: row.get("source_type") or "")
        return {
            "sources": source_rows,
            "api_key_status": {
                "semantic_scholar": bool(settings.semantic_scholar_api_key),
                "gnews": bool(settings.gnews_api_key),
                "newsapi": bool(settings.newsapi_key),
                "github": bool(settings.github_token),
                "apify": bool(settings.apify_api_token),
                "huggingface": bool(settings.huggingface_token),
                "exa": bool(settings.exa_api_key),
            },
            "logs": fetch_logs[:20],
        }

    def _with_db(self, operation: Callable[[Any], Any]) -> Any:
        if not self.use_postgres:
            return None
        try:
            from database.connection import get_db_context

            with get_db_context() as db:
                result = operation(db)
                db.commit()
                return result
        except Exception as exc:
            logger.debug(f"Postgres intelligence store unavailable, using local fallback: {exc}")
            return None

    def _db_insert_brief(self, db: Any, brief: Dict[str, Any]) -> bool:
        db.execute(
            text(
                """
                INSERT INTO uploaded_briefs (
                    id, file_name, file_type, file_size_bytes, content_text, parsed_summary,
                    metadata, processing_status, processing_error, created_at, updated_at
                ) VALUES (
                    :id, :file_name, :file_type, :file_size_bytes, :content_text, :parsed_summary,
                    CAST(:metadata AS jsonb), :processing_status, :processing_error, :created_at, :updated_at
                )
                """
            ),
            {**brief, "metadata": json.dumps(brief["metadata"])},
        )
        return True

    def _db_get_brief(self, db: Any, brief_id: str) -> Optional[Dict[str, Any]]:
        row = db.execute(
            text("SELECT * FROM uploaded_briefs WHERE id = :id"),
            {"id": brief_id},
        ).mappings().first()
        return dict(row) if row else None

    def _db_update_brief(self, db: Any, brief_id: str, updates: Dict[str, Any]) -> bool:
        allowed = {"parsed_summary", "metadata", "processing_status", "processing_error", "updated_at"}
        assignments = []
        params = {"id": brief_id}
        for key, value in updates.items():
            if key not in allowed:
                continue
            if key == "metadata":
                assignments.append("metadata = CAST(:metadata AS jsonb)")
                params[key] = json.dumps(value)
            else:
                assignments.append(f"{key} = :{key}")
                params[key] = value
        if not assignments:
            return True
        db.execute(text(f"UPDATE uploaded_briefs SET {', '.join(assignments)} WHERE id = :id"), params)
        return True

    def _db_save_topics(self, db: Any, brief_id: str, records: List[Dict[str, Any]]) -> bool:
        db.execute(text("DELETE FROM brief_extracted_topics WHERE brief_id = :brief_id"), {"brief_id": brief_id})
        for record in records:
            db.execute(
                text(
                    """
                    INSERT INTO brief_extracted_topics (
                        id, brief_id, topic, category, confidence_score, created_at, updated_at
                    ) VALUES (
                        :id, :brief_id, :topic, :category, :confidence_score, :created_at, :updated_at
                    )
                    """
                ),
                record,
            )
        return True

    def _db_get_topics(self, db: Any, brief_id: str) -> List[Dict[str, Any]]:
        rows = db.execute(
            text("SELECT * FROM brief_extracted_topics WHERE brief_id = :brief_id ORDER BY confidence_score DESC"),
            {"brief_id": brief_id},
        ).mappings().all()
        return [dict(row) for row in rows]

    def _db_save_recommendations(self, db: Any, brief_id: str, records: List[Dict[str, Any]]) -> bool:
        db.execute(text("DELETE FROM brief_recommendations WHERE brief_id = :brief_id"), {"brief_id": brief_id})
        for record in records:
            db.execute(
                text(
                    """
                    INSERT INTO brief_recommendations (
                        id, brief_id, technology_name, category, summary, recommendation,
                        confidence_score, implementation_difficulty, final_score, alternatives,
                        risks_tradeoffs, suggested_architecture, next_steps, citations,
                        scoring_breakdown, status, created_at, updated_at
                    ) VALUES (
                        :id, :brief_id, :technology_name, :category, :summary, :recommendation,
                        :confidence_score, :implementation_difficulty, :final_score, :alternatives,
                        :risks_tradeoffs, :suggested_architecture, :next_steps, CAST(:citations AS jsonb),
                        CAST(:scoring_breakdown AS jsonb), :status, :created_at, :updated_at
                    )
                    """
                ),
                {
                    **record,
                    "citations": json.dumps(record["citations"]),
                    "scoring_breakdown": json.dumps(record["scoring_breakdown"]),
                },
            )
        return True

    def _db_get_recommendations(self, db: Any, brief_id: str) -> List[Dict[str, Any]]:
        rows = db.execute(
            text("SELECT * FROM brief_recommendations WHERE brief_id = :brief_id ORDER BY final_score DESC"),
            {"brief_id": brief_id},
        ).mappings().all()
        return [dict(row) for row in rows]

    def _db_get_recommendation(self, db: Any, recommendation_id: str) -> Optional[Dict[str, Any]]:
        row = db.execute(
            text("SELECT * FROM brief_recommendations WHERE id = :id"),
            {"id": recommendation_id},
        ).mappings().first()
        return dict(row) if row else None

    def _db_save_technology_radar(self, db: Any, radar_items: List[Dict[str, Any]]) -> bool:
        for item in radar_items:
            db.execute(
                text(
                    """
                    INSERT INTO technologies (
                        name, category, description, evidence_score, recency_score,
                        adoption_signal, source_count, radar_stage, metadata, updated_at
                    ) VALUES (
                        :name, :category, :description, :evidence_score, :recency_score,
                        :adoption_signal, :source_count, :radar_stage, CAST(:metadata AS jsonb), NOW()
                    )
                    ON CONFLICT (name) DO UPDATE SET
                        category = EXCLUDED.category,
                        description = EXCLUDED.description,
                        evidence_score = EXCLUDED.evidence_score,
                        recency_score = EXCLUDED.recency_score,
                        adoption_signal = EXCLUDED.adoption_signal,
                        source_count = EXCLUDED.source_count,
                        radar_stage = EXCLUDED.radar_stage,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """
                ),
                {
                    **item,
                    "metadata": json.dumps({"sources": item.get("sources", [])}),
                },
            )
        return True

    def _db_get_technology_radar(self, db: Any) -> List[Dict[str, Any]]:
        rows = db.execute(
            text(
                """
                SELECT name, category, description, evidence_score, recency_score,
                       adoption_signal, source_count, radar_stage, metadata, updated_at
                FROM technologies
                ORDER BY evidence_score DESC, source_count DESC, updated_at DESC
                LIMIT 80
                """
            )
        ).mappings().all()
        return [dict(row) for row in rows]

    def _db_query_sources(self, db: Any, query_terms: List[str], limit: int) -> List[Dict[str, Any]]:
        terms = [term.lower() for term in query_terms if term][:10]
        if not terms:
            return []
        predicates = []
        params: Dict[str, Any] = {"limit": limit}
        for index, term_value in enumerate(terms):
            key = f"term_{index}"
            predicates.append(
                f"LOWER(COALESCE(title, '') || ' ' || COALESCE(parsed_text, '') || ' ' || COALESCE(metadata::text, '')) LIKE :{key}"
            )
            params[key] = f"%{term_value}%"
        sql = f"""
            SELECT id, url, title, authors, publication_date, source_type, domain, tier,
                   credibility_score, citation_count, parsed_text, metadata, created_at, updated_at
            FROM sources
            WHERE {' OR '.join(predicates)}
            ORDER BY publication_date DESC NULLS LAST, credibility_score DESC, created_at DESC
            LIMIT :limit
        """
        rows = db.execute(text(sql), params).mappings().all()
        return [_source_row_to_document(row) for row in rows]

    def _db_research_feed(
        self,
        db: Any,
        query: Optional[str],
        source_type: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        predicates = []
        params: Dict[str, Any] = {"limit": limit}
        if query:
            predicates.append(
                "LOWER(COALESCE(title, '') || ' ' || COALESCE(parsed_text, '') || ' ' || COALESCE(metadata::text, '')) LIKE :query"
            )
            params["query"] = f"%{query.lower()}%"
        if source_type:
            predicates.append("source_type = :source_type")
            params["source_type"] = source_type
        where_sql = f"WHERE {' AND '.join(predicates)}" if predicates else ""
        rows = db.execute(
            text(
                f"""
                SELECT id, url, title, authors, publication_date, source_type, domain, tier,
                       credibility_score, citation_count, parsed_text, metadata, created_at, updated_at
                FROM sources
                {where_sql}
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()
        return [_source_row_to_document(row) for row in rows]

    def _db_save_daily_report(self, db: Any, report: Dict[str, Any]) -> bool:
        db.execute(
            text(
                """
                INSERT INTO daily_intelligence_reports (
                    id, report_date, subject, summary, top_updates, worth_exploring,
                    emerging_signals, ignore_for_now, html_body, markdown_body, citations,
                    processing_status, created_at, updated_at
                ) VALUES (
                    :id, :report_date, :subject, :summary, CAST(:top_updates AS jsonb), CAST(:worth_exploring AS jsonb),
                    CAST(:emerging_signals AS jsonb), CAST(:ignore_for_now AS jsonb), :html_body, :markdown_body,
                    CAST(:citations AS jsonb), :processing_status, :created_at, :updated_at
                )
                """
            ),
            {
                **report,
                "top_updates": json.dumps(report["top_updates"]),
                "worth_exploring": json.dumps(report["worth_exploring"]),
                "emerging_signals": json.dumps(report["emerging_signals"]),
                "ignore_for_now": json.dumps(report["ignore_for_now"]),
                "citations": json.dumps(report["citations"]),
            },
        )
        return True

    def _db_latest_daily_report(self, db: Any) -> Optional[Dict[str, Any]]:
        row = db.execute(
            text("SELECT * FROM daily_intelligence_reports ORDER BY created_at DESC LIMIT 1")
        ).mappings().first()
        return dict(row) if row else None

    def _db_list_daily_reports(self, db: Any, limit: int) -> List[Dict[str, Any]]:
        rows = db.execute(
            text("SELECT * FROM daily_intelligence_reports ORDER BY created_at DESC LIMIT :limit"),
            {"limit": limit},
        ).mappings().all()
        return [dict(row) for row in rows]

    def _db_save_email_log(self, db: Any, record: Dict[str, Any]) -> bool:
        db.execute(
            text(
                """
                INSERT INTO sent_email_logs (
                    id, report_id, recipient_email, provider, subject, status,
                    error_message, sent_at, created_at, updated_at
                ) VALUES (
                    :id, :report_id, :recipient_email, :provider, :subject, :status,
                    :error_message, :sent_at, :created_at, :updated_at
                )
                """
            ),
            record,
        )
        return True

    def _db_list_email_logs(self, db: Any, limit: int) -> List[Dict[str, Any]]:
        rows = db.execute(
            text("SELECT * FROM sent_email_logs ORDER BY created_at DESC LIMIT :limit"),
            {"limit": limit},
        ).mappings().all()
        return [dict(row) for row in rows]

    def _db_get_team_email_settings(self, db: Any) -> Optional[Dict[str, Any]]:
        row = db.execute(
            text("SELECT * FROM team_email_settings ORDER BY updated_at DESC LIMIT 1")
        ).mappings().first()
        return dict(row) if row else None

    def _db_save_team_email_settings(self, db: Any, record: Dict[str, Any]) -> bool:
        db.execute(
            text(
                """
                INSERT INTO team_email_settings (
                    id, team_email, send_time, timezone, topics, enabled, provider,
                    updated_by, created_at, updated_at
                ) VALUES (
                    :id, :team_email, :send_time, :timezone, :topics, :enabled, :provider,
                    :updated_by, :created_at, :updated_at
                )
                ON CONFLICT (id) DO UPDATE SET
                    team_email = EXCLUDED.team_email,
                    send_time = EXCLUDED.send_time,
                    timezone = EXCLUDED.timezone,
                    topics = EXCLUDED.topics,
                    enabled = EXCLUDED.enabled,
                    provider = EXCLUDED.provider,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = EXCLUDED.updated_at
                """
            ),
            record,
        )
        return True

    def _db_dashboard_overview(self, db: Any) -> Dict[str, Any]:
        stats = db.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total_sources,
                    COUNT(*) FILTER (WHERE ingestion_status IN ('pending', 'processing', 'completed')) AS active_sources,
                    COUNT(*) FILTER (WHERE created_at::date = CURRENT_DATE) AS today,
                    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') AS this_week
                FROM sources
                """
            )
        ).mappings().first()
        latest_papers = self._db_research_feed(db, None, "arxiv", 5)
        latest_tools = self._db_research_feed(db, None, "github", 5)
        latest_news = self._db_research_feed(db, None, None, 10)
        news_types = {"gnews", "newsapi", "rss_feed", "google_news", "hackernews", "guardian", "nytimes", "gdelt"}
        latest_market_news = [item for item in latest_news if item.get("source_type") in news_types][:5]
        fetch_rows = db.execute(
            text(
                """
                SELECT status, COUNT(*) AS count
                FROM fetch_logs
                WHERE fetch_timestamp >= NOW() - INTERVAL '7 days'
                GROUP BY status
                """
            )
        ).mappings().all()
        total_fetches = sum(row["count"] for row in fetch_rows)
        success_fetches = sum(row["count"] for row in fetch_rows if row["status"] == "success")
        latest_email = self._db_list_email_logs(db, 1)
        latest_report = self._db_latest_daily_report(db)
        return {
            "total_sources_monitored": stats["total_sources"] if stats else 0,
            "active_sources": stats["active_sources"] if stats else 0,
            "items_ingested_today": stats["today"] if stats else 0,
            "items_ingested_this_week": stats["this_week"] if stats else 0,
            "latest_papers": latest_papers,
            "latest_tools": latest_tools,
            "latest_market_news": latest_market_news,
            "trending_technologies": self._db_get_technology_radar(db)[:8],
            "system_health": {"status": "operational"},
            "ingestion_success_rate": round(success_fetches / total_fetches, 3) if total_fetches else None,
            "email_delivery_status": latest_email[0] if latest_email else None,
            "latest_daily_report": latest_report,
        }

    def _db_source_management(self, db: Any) -> Dict[str, Any]:
        rows = db.execute(
            text(
                """
                SELECT source_type, MAX(fetch_timestamp) AS last_fetch_time,
                       COUNT(*) AS fetch_count,
                       SUM(items_fetched) AS items_fetched,
                       MAX(status) AS latest_status,
                       MAX(error_message) AS last_error
                FROM fetch_logs
                GROUP BY source_type
                ORDER BY source_type
                """
            )
        ).mappings().all()
        return {
            "sources": [dict(row) for row in rows],
            "api_key_status": {
                "semantic_scholar": bool(settings.semantic_scholar_api_key),
                "gnews": bool(settings.gnews_api_key),
                "newsapi": bool(settings.newsapi_key),
                "github": bool(settings.github_token),
                "apify": bool(settings.apify_api_token),
                "huggingface": bool(settings.huggingface_token),
            },
            "logs": [dict(row) for row in rows[:20]],
        }

    def _ensure_local_store(self) -> None:
        self.local_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.local_path.exists():
            self._write_local(_empty_local_store())

    def _read_local(self) -> Dict[str, Any]:
        with self._lock:
            if not self.local_path.exists():
                return _empty_local_store()
            try:
                with self.local_path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except json.JSONDecodeError:
                logger.warning(f"Local intelligence store was invalid JSON: {self.local_path}")
                data = _empty_local_store()
            merged = _empty_local_store()
            merged.update(data)
            return merged

    def _read_local_sources(self) -> List[Dict[str, Any]]:
        if not self.local_sources_path.exists():
            return []
        try:
            with self.local_sources_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(f"Local source store unavailable: {exc}")
            return []
        sources = data.get("sources", [])
        if not isinstance(sources, list):
            return []
        return [source for source in sources if isinstance(source, dict)]

    def _read_local_fetch_logs(self) -> List[Dict[str, Any]]:
        if not self.local_sources_path.exists():
            return []
        try:
            with self.local_sources_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return []
        logs = data.get("fetch_logs", [])
        if not isinstance(logs, list):
            return []
        return sorted(
            [log for log in logs if isinstance(log, dict)],
            key=lambda item: item.get("fetch_timestamp") or "",
            reverse=True,
        )

    def _write_local(self, data: Dict[str, Any]) -> None:
        with self._lock:
            self.local_path.parent.mkdir(parents=True, exist_ok=True)
            with self.local_path.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, default=str)

    def _local_get(self, collection: str, item_id: str) -> Optional[Dict[str, Any]]:
        for item in self._read_local().get(collection, []):
            if item.get("id") == item_id:
                return item
        return None

    def _local_upsert(self, collection: str, item: Dict[str, Any]) -> None:
        data = self._read_local()
        items = [existing for existing in data.get(collection, []) if existing.get("id") != item.get("id")]
        items.append(item)
        data[collection] = items
        self._write_local(data)

    def _local_update(self, collection: str, item_id: str, updates: Dict[str, Any]) -> None:
        data = self._read_local()
        for item in data.get(collection, []):
            if item.get("id") == item_id:
                item.update(updates)
        self._write_local(data)

    def _local_replace_by(self, collection: str, field: str, value: Any, records: List[Dict[str, Any]]) -> None:
        data = self._read_local()
        data[collection] = [item for item in data.get(collection, []) if item.get(field) != value] + records
        self._write_local(data)

    def _local_replace_all(self, collection: str, records: List[Dict[str, Any]]) -> None:
        data = self._read_local()
        data[collection] = records
        self._write_local(data)


def _source_row_to_document(row: Dict[str, Any]) -> Dict[str, Any]:
    metadata = row.get("metadata") or {}
    return {
        "id": str(row.get("id")),
        "url": row.get("url"),
        "title": row.get("title"),
        "authors": row.get("authors") or [],
        "publication_date": str(row.get("publication_date") or ""),
        "source_type": row.get("source_type"),
        "domain": row.get("domain"),
        "tier": row.get("tier"),
        "credibility_score": row.get("credibility_score") or 0,
        "citation_count": row.get("citation_count") or 0,
        "content": row.get("parsed_text") or "",
        "parsed_text": row.get("parsed_text") or "",
        "metadata": metadata,
        "created_at": str(row.get("created_at") or ""),
        "updated_at": str(row.get("updated_at") or ""),
    }


def _local_source_document(source: Dict[str, Any]) -> Dict[str, Any]:
    metadata = source.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    content = source.get("content") or source.get("abstract") or source.get("parsed_text") or ""
    return {
        "id": str(source.get("id") or source.get("dedupe_hash") or source.get("url") or ""),
        "url": source.get("url"),
        "title": source.get("title"),
        "authors": source.get("authors") or [],
        "publication_date": str(source.get("publication_date") or ""),
        "source_type": source.get("source_type"),
        "domain": source.get("domain") or metadata.get("domain"),
        "tier": source.get("tier"),
        "credibility_score": source.get("credibility_score") or 0,
        "citation_count": source.get("citation_count") or metadata.get("citation_count", 0),
        "content": content,
        "parsed_text": content,
        "metadata": metadata,
        "created_at": str(source.get("created_at") or source.get("fetched_at") or ""),
        "updated_at": str(source.get("updated_at") or ""),
        "fetched_at": str(source.get("fetched_at") or source.get("created_at") or ""),
    }


def _source_search_text(source: Dict[str, Any]) -> str:
    return " ".join(
        str(part or "")
        for part in [
            source.get("title"),
            source.get("content"),
            source.get("abstract"),
            source.get("parsed_text"),
            source.get("source_type"),
            source.get("metadata"),
        ]
    ).lower()


def _query_tokens(values: List[str]) -> set[str]:
    return {
        token
        for value in values
        for token in re.findall(r"[a-z0-9][a-z0-9+-]{2,}", str(value).lower())
        if token not in {"the", "and", "for", "with", "from", "this", "that", "into"}
    }


def _date_sort_value(value: Any) -> float:
    parsed = _parse_datetime(value)
    return parsed.timestamp() if parsed else 0.0


def _is_today(value: Any) -> bool:
    parsed = _parse_datetime(value)
    return bool(parsed and parsed.date() == datetime.now(timezone.utc).date())


def _is_this_week(value: Any) -> bool:
    parsed = _parse_datetime(value)
    if not parsed:
        return False
    return parsed >= datetime.now(timezone.utc) - timedelta(days=7)


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text_value = str(value).strip()
    if not text_value:
        return None
    for candidate in (text_value, text_value[:19], text_value[:10]):
        try:
            parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        return datetime.strptime(text_value[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _default_team_email_settings() -> Dict[str, Any]:
    send_time = f"{settings.daily_intelligence_send_hour:02d}:{settings.daily_intelligence_send_minute:02d}"
    return {
        "id": None,
        "team_email": "",
        "send_time": send_time,
        "timezone": settings.daily_intelligence_timezone,
        "topics": settings.daily_intelligence_topics,
        "enabled": settings.daily_intelligence_enabled,
        "provider": settings.email_provider,
        "updated_by": "system",
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
    }


def _empty_local_store() -> Dict[str, Any]:
    return {
        "briefs": [],
        "brief_topics": [],
        "brief_recommendations": [],
        "technologies": [],
        "daily_reports": [],
        "email_logs": [],
        "team_email_settings": _default_team_email_settings(),
    }


_store_instance: Optional[IntelligenceStore] = None


def get_store() -> IntelligenceStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = IntelligenceStore()
    return _store_instance
