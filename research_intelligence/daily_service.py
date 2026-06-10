"""Daily AI and RAG market intelligence report generation."""
from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from config import get_settings
from ingestion.source_orchestrator import SourceOrchestrator
from research_intelligence.emailer import (
    EmailDeliveryError,
    EmailSender,
    build_daily_email_html,
    build_daily_email_markdown,
)
from research_intelligence.scoring import rank_source_documents
from research_intelligence.store import IntelligenceStore, get_store, utc_now_iso


settings = get_settings()

DEFAULT_DAILY_SOURCES = ["rss", "google_news", "arxiv", "openalex", "github", "hackernews"]

CATEGORY_KEYWORDS = {
    "Model Release": {"model", "gpt", "claude", "gemini", "llama", "mistral", "cohere", "openai", "anthropic"},
    "RAG": {"rag", "retrieval", "embedding", "vector", "rerank", "chunk"},
    "Agents": {"agent", "tool use", "workflow", "automation", "multi-agent"},
    "Developer Tools": {"github", "sdk", "api", "framework", "library", "developer"},
    "Research": {"paper", "arxiv", "benchmark", "evaluation", "dataset"},
    "Market": {"funding", "startup", "acquisition", "enterprise", "adoption"},
    "Security": {"security", "privacy", "compliance", "regulation", "safety"},
}


class DailyIntelligenceService:
    """Fetch, rank, summarize, store, and send daily intelligence reports."""

    def __init__(self, store: Optional[IntelligenceStore] = None) -> None:
        self.store = store or get_store()
        self.fetch_warnings: List[str] = []
        self.source_status: List[Dict[str, Any]] = []

    async def generate_daily_report(self, topics: Optional[List[str]] = None) -> Dict[str, Any]:
        selected_topics = topics or settings.daily_intelligence_topics
        fetched = await self._fetch_latest(selected_topics)
        db_docs = self.store.query_sources(selected_topics, limit=120)
        documents = _dedupe_documents([*fetched, *db_docs])
        ranked = rank_source_documents(documents, query_terms=selected_topics)

        updates = [_build_update(item) for item in ranked[:60] if _valid_result_url(item.get("url"))]
        top_updates = updates[:20]
        worth_exploring = [item for item in updates[20:35] if item["impact_score"] >= 0.35][:5]
        emerging_signals = _emerging_signals(updates)
        ignore_for_now = _ignore_for_now(ranked)
        report_date = date.today().isoformat()
        subject = f"Daily AI Intelligence Brief - {report_date}"

        report = {
            "report_date": report_date,
            "subject": subject,
            "summary": _summary_for(top_updates, selected_topics),
            "top_updates": top_updates,
            "worth_exploring": worth_exploring,
            "emerging_signals": emerging_signals,
            "ignore_for_now": ignore_for_now,
            "source_status": self.source_status,
            "warnings": self.fetch_warnings,
            "citations": [
                {"title": item.get("title"), "url": item.get("url"), "source_type": item.get("source_type")}
                for item in top_updates
                if item.get("url")
            ],
            "processing_status": "completed",
        }
        report["html_body"] = build_daily_email_html(report)
        report["markdown_body"] = build_daily_email_markdown(report)
        return self.store.save_daily_report(report)

    def get_daily_report(self) -> Optional[Dict[str, Any]]:
        return self.store.get_latest_daily_report()

    async def send_now(self, topics: Optional[List[str]] = None) -> Dict[str, Any]:
        settings_record = self.store.get_team_email_settings()
        report = await self.generate_daily_report(topics=topics or settings_record.get("topics"))
        sender = EmailSender(provider=settings_record.get("provider") or settings.email_provider)
        recipient = settings_record.get("team_email")
        try:
            delivery = await sender.send(
                to_email=recipient,
                subject=report["subject"],
                html_body=report["html_body"],
                text_body=report["markdown_body"],
            )
            status = "sent"
            error_message = None
            provider = delivery.get("provider", sender.provider)
            sent_at = utc_now_iso()
        except EmailDeliveryError as exc:
            status = "failed"
            error_message = str(exc)
            provider = sender.provider
            sent_at = None

        email_log = self.store.save_email_log(
            {
                "report_id": report["id"],
                "recipient_email": recipient,
                "provider": provider,
                "subject": report["subject"],
                "status": status,
                "error_message": error_message,
                "sent_at": sent_at,
            }
        )
        return {"report": report, "email_log": email_log}

    def email_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.store.list_email_logs(limit=limit)

    async def _fetch_latest(self, topics: List[str]) -> List[Dict[str, Any]]:
        try:
            orchestrator = SourceOrchestrator()
            documents = await orchestrator.fetch_all_sources(
                keywords=topics[:5],
                enable_apify=False,
                sources=DEFAULT_DAILY_SOURCES,
            )
            self.source_status = orchestrator.last_fetch_details
            self.fetch_warnings = [
                f"{item.get('source_id')}: {item.get('error') or 'no items returned'}"
                for item in self.source_status
                if item.get("status") in {"failed", "skipped"}
            ]
            return documents
        except Exception as exc:
            message = f"Daily intelligence source fetch failed: {exc}"
            logger.warning(message)
            self.fetch_warnings = [message]
            return []


def _dedupe_documents(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped = []
    for document in documents:
        if not _valid_result_url(document.get("url")):
            continue
        key = _normalize_key(document.get("url") or document.get("title") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(document)
    return deduped


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _build_update(document: Dict[str, Any]) -> Dict[str, Any]:
    text = " ".join(str(part or "") for part in [document.get("title"), document.get("content"), document.get("abstract")])
    tags = _category_tags(text, document.get("source_type", ""))
    score = float(document.get("final_score", 0))
    metadata = document.get("metadata") or {}
    return {
        "title": document.get("title") or "Untitled update",
        "url": document.get("url"),
        "source_link": document.get("url"),
        "source_type": document.get("source_type", "unknown"),
        "category": tags[0] if tags else _format_source_type(document.get("source_type", "unknown")),
        "publication_date": str(document.get("publication_date") or ""),
        "category_tags": tags,
        "impact_score": round(score, 3),
        "brief": _brief_from_document(text),
        "why_it_matters": _why_update_matters(text, tags, score),
        "recommended_action": _recommended_action(tags, score),
        "source_credibility": document.get("credibility_score", 0),
        "thumbnail_url": _thumbnail_from_metadata(metadata),
    }


def _category_tags(text: str, source_type: str) -> List[str]:
    text_lower = text.lower()
    tags = [
        category
        for category, keywords in CATEGORY_KEYWORDS.items()
        if any(keyword in text_lower for keyword in keywords)
    ]
    if source_type in {"arxiv", "openalex", "semantic_scholar", "papers_with_code"} and "Research" not in tags:
        tags.append("Research")
    if source_type == "github" and "Developer Tools" not in tags:
        tags.append("Developer Tools")
    return tags[:4] or ["AI"]


def _why_update_matters(text: str, tags: List[str], score: float) -> str:
    primary = tags[0] if tags else "AI"
    if score >= 0.7:
        return f"High-confidence {primary.lower()} signal with strong relevance, source quality, or adoption evidence."
    if score >= 0.45:
        return f"Relevant {primary.lower()} signal worth monitoring for near-term planning."
    return f"Early {primary.lower()} signal; useful context but needs more supporting evidence."


def _recommended_action(tags: List[str], score: float) -> str:
    if score >= 0.72:
        return "Review with the team and decide whether it changes the roadmap."
    if "Research" in tags:
        return "Skim the paper and capture implementation implications."
    if "Developer Tools" in tags:
        return "Run a lightweight repository or docs review."
    if "Security" in tags:
        return "Check whether policy, privacy, or compliance assumptions need updates."
    return "Monitor and revisit if more sources confirm the signal."


def _summary_for(top_updates: List[Dict[str, Any]], topics: List[str]) -> str:
    if not top_updates:
        return f"No high-confidence updates were found for {', '.join(topics[:4])} today."
    categories = Counter(tag for update in top_updates for tag in update.get("category_tags", []))
    focus = ", ".join(category for category, _ in categories.most_common(3))
    return f"{len(top_updates)} prioritized updates across {focus or ', '.join(topics[:3])}."


def _brief_from_document(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return "No summary text was provided by the source."
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    summary = " ".join(sentence for sentence in sentences[:3] if sentence).strip()
    return summary[:420]


def _thumbnail_from_metadata(metadata: Dict[str, Any]) -> Optional[str]:
    for key in ("image_url", "socialimage", "thumbnail", "thumbnail_url", "og_image", "avatar_url"):
        value = metadata.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    return None


def _valid_result_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def _format_source_type(value: str) -> str:
    return str(value or "source").replace("_", " ").title()


def _emerging_signals(updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    tag_counts = Counter(tag for update in updates for tag in update.get("category_tags", []))
    signals = []
    for tag, count in tag_counts.most_common(5):
        if count < 2:
            continue
        matching = next((update for update in updates if tag in update.get("category_tags", [])), None)
        if matching:
            signals.append(
                {
                    "title": f"{tag} appeared in {count} sources",
                    "url": matching.get("url"),
                    "category_tags": [tag],
                    "impact_score": matching.get("impact_score", 0),
                }
            )
    return signals[:5]


def _ignore_for_now(ranked_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ignored = []
    for document in ranked_documents:
        breakdown = document.get("scoring_breakdown", {})
        if breakdown.get("hype_penalty", 0) >= 0.06 or document.get("final_score", 0) < 0.3:
            ignored.append(
                {
                    "title": document.get("title") or "Untitled",
                    "url": document.get("url"),
                    "category_tags": ["Low confidence"],
                    "impact_score": round(document.get("final_score", 0), 3),
                    "why_it_matters": "Low evidence score, unsupported hype language, or weak relevance.",
                    "recommended_action": "Ignore until higher-quality sources confirm it.",
                }
            )
        if len(ignored) >= 5:
            break
    return ignored
