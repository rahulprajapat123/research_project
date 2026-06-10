"""Project brief upload, analysis, and recommendation report service."""
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from config import get_settings
from ingestion.source_classifier import classify_source_tier
from ingestion.source_orchestrator import SourceOrchestrator
from research_intelligence.parsing import (
    BriefParsingError,
    build_search_terms,
    extract_brief_insights,
    parse_brief_file,
)
from research_intelligence.scoring import (
    build_technology_radar,
    build_technology_recommendations,
    rank_source_documents,
)
from research_intelligence.store import IntelligenceStore, get_store


settings = get_settings()


class BriefIntelligenceService:
    """Coordinates upload parsing, evidence retrieval, and report generation."""

    def __init__(self, store: Optional[IntelligenceStore] = None) -> None:
        self.store = store or get_store()
        self.fetch_warnings: List[str] = []
        self.source_status: List[Dict[str, Any]] = []

    async def upload_brief(self, file_name: str, content: bytes) -> Dict[str, Any]:
        parsed = parse_brief_file(
            file_name=file_name,
            content=content,
            max_size_mb=settings.max_brief_upload_size_mb,
        )
        insights = extract_brief_insights(parsed.content_text)
        brief = self.store.create_brief(
            file_name=parsed.file_name,
            file_type=parsed.file_type,
            file_size_bytes=len(content),
            content_text=parsed.content_text,
            metadata={**parsed.metadata, "insights": insights},
        )
        topics = _topics_to_records(insights)
        self.store.save_brief_topics(brief["id"], topics)
        self.store.update_brief(
            brief["id"],
            parsed_summary=_summary_from_insights(insights),
            metadata={**parsed.metadata, "insights": insights},
            processing_status="parsed",
        )
        return {
            "brief_id": brief["id"],
            "file_name": parsed.file_name,
            "file_type": parsed.file_type,
            "processing_status": "parsed",
            "parsed_summary": _summary_from_insights(insights),
            "extracted_topics": topics,
            "project_profile": insights,
        }

    def get_brief(self, brief_id: str) -> Optional[Dict[str, Any]]:
        brief = self.store.get_brief(brief_id)
        if not brief:
            return None
        return {
            **_brief_public_view(brief),
            "extracted_topics": self.store.get_brief_topics(brief_id),
            "recommendations": self.store.get_recommendations(brief_id),
        }

    async def analyze_brief(self, brief_id: str, refresh_sources: bool = True) -> Dict[str, Any]:
        brief = self.store.get_brief(brief_id)
        if not brief:
            raise KeyError("Brief not found")

        try:
            self.store.update_brief(brief_id, processing_status="analyzing", processing_error=None)
            self.fetch_warnings = []
            self.source_status = []
            insights = _brief_insights(brief)
            if not insights:
                insights = extract_brief_insights(brief.get("content_text", ""))

            query_terms = build_search_terms(insights)
            db_sources = self.store.query_sources(query_terms, limit=80)
            external_sources = await self._fetch_external_sources(query_terms) if refresh_sources else []
            sources = _dedupe_sources([*_normalize_sources(db_sources), *_normalize_sources(external_sources)])

            ranked_sources = [
                source
                for source in rank_source_documents(sources, query_terms=query_terms)
                if _valid_result_url(source.get("url"))
            ]
            recommendations = build_technology_recommendations(
                documents=ranked_sources,
                brief_insights=insights,
                query_terms=query_terms,
                max_recommendations=8,
            )

            stored_recommendations = self.store.save_recommendations(brief_id, recommendations)
            radar_items = build_technology_radar(recommendations)
            if radar_items:
                self.store.save_technology_radar(radar_items)

            report = self._build_report(
                brief=brief,
                insights=insights,
                query_terms=query_terms,
                ranked_sources=ranked_sources,
                recommendations=stored_recommendations,
                radar_items=radar_items,
            )
            self.store.update_brief(
                brief_id,
                parsed_summary=report["executive_summary"],
                metadata={**(brief.get("metadata") or {}), "insights": insights, "last_report": report},
                processing_status="completed",
                processing_error=None,
            )
            return report
        except Exception as exc:
            logger.error(f"Brief analysis failed for {brief_id}: {exc}", exc_info=True)
            self.store.update_brief(brief_id, processing_status="failed", processing_error=str(exc))
            if isinstance(exc, BriefParsingError):
                raise
            raise

    def get_recommendations(self, brief_id: str) -> List[Dict[str, Any]]:
        return self.store.get_recommendations(brief_id)

    async def _fetch_external_sources(self, query_terms: List[str]) -> List[Dict[str, Any]]:
        sources = ["arxiv", "semantic_scholar", "openalex", "rss", "google_news", "github", "hackernews", "exa"]
        try:
            orchestrator = SourceOrchestrator()
            return await asyncio.wait_for(
                orchestrator.fetch_all_sources(
                    keywords=query_terms[:5],
                    enable_apify=False,
                    sources=sources,
                ),
                timeout=90,  # Increased from 45s - arXiv alone can take 15-20s
            )
        except asyncio.TimeoutError:
            message = "Source fetch timed out after 90 seconds. Try narrower keywords or fewer sources."
            logger.error(message)
            self.fetch_warnings.append(message)
            return []
        except Exception as exc:
            message = f"External source fetch failed during brief analysis: {type(exc).__name__}: {exc}"
            logger.error(message)
            self.fetch_warnings.append(message)
            return []
        finally:
            if "orchestrator" in locals():
                self.source_status = orchestrator.last_fetch_details
                self.fetch_warnings.extend(
                    f"{item.get('source_id')}: {item.get('error') or 'no items returned'}"
                    for item in self.source_status
                    if item.get("status") in {"failed", "skipped"}
                )

    def _build_report(
        self,
        brief: Dict[str, Any],
        insights: Dict[str, Any],
        query_terms: List[str],
        ranked_sources: List[Dict[str, Any]],
        recommendations: List[Dict[str, Any]],
        radar_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if recommendations:
            summary = (
                f"Found {len(ranked_sources)} relevant resources and {len(recommendations)} citation-backed "
                f"technology signals for {insights.get('domain', 'the project')}."
            )
        else:
            summary = (
                "No technology recommendation was generated. Review the fetched resource list and warnings, "
                "then broaden the brief topics or configure missing source credentials if needed."
            )

        architecture = _suggest_project_architecture(recommendations, insights)
        risk_items = _aggregate_risks(recommendations, insights)
        next_steps = _aggregate_next_steps(recommendations)
        resource_results = [_resource_result(source, insights, query_terms) for source in ranked_sources[:30]]

        return {
            "brief_id": brief["id"],
            "file_name": brief.get("file_name"),
            "processing_status": "completed",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "executive_summary": summary,
            "project_profile": insights,
            "query_terms": query_terms,
            "evidence_sources_count": len(ranked_sources),
            "resource_results": resource_results,
            "results": resource_results,
            "top_evidence_sources": resource_results[:12],
            "recommended_technologies": recommendations,
            "technology_radar": radar_items,
            "suggested_architecture": architecture,
            "risks_and_tradeoffs": risk_items,
            "next_implementation_steps": next_steps,
            "source_status": self.source_status,
            "warnings": self.fetch_warnings,
        }


def _brief_public_view(brief: Dict[str, Any]) -> Dict[str, Any]:
    metadata = brief.get("metadata") or {}
    if isinstance(metadata, str):
        metadata = {}
    return {
        "id": str(brief.get("id")),
        "file_name": brief.get("file_name"),
        "file_type": brief.get("file_type"),
        "file_size_bytes": brief.get("file_size_bytes"),
        "parsed_summary": brief.get("parsed_summary"),
        "processing_status": brief.get("processing_status"),
        "processing_error": brief.get("processing_error"),
        "project_profile": metadata.get("insights", {}),
        "created_at": str(brief.get("created_at") or ""),
        "updated_at": str(brief.get("updated_at") or ""),
    }


def _brief_insights(brief: Dict[str, Any]) -> Dict[str, Any]:
    metadata = brief.get("metadata") or {}
    if isinstance(metadata, str):
        return {}
    return metadata.get("insights") or {}


def _topics_to_records(insights: Dict[str, Any]) -> List[Dict[str, Any]]:
    topics = []
    for topic in insights.get("key_topics", []):
        topics.append({"topic": topic, "category": "technical", "confidence_score": insights.get("confidence_score", 0.7)})
    for requirement in insights.get("technical_requirements", [])[:5]:
        topics.append({"topic": requirement, "category": "requirement", "confidence_score": 0.65})
    return topics[:15]


def _summary_from_insights(insights: Dict[str, Any]) -> str:
    domain = insights.get("domain", "general")
    topics = ", ".join(insights.get("key_topics", [])[:4]) or "research intelligence"
    return f"{domain.title()} brief focused on {topics}."


def _normalize_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    for source in sources:
        url = source.get("url") or ""
        title = source.get("title") or "Untitled source"
        metadata = source.get("metadata") or {}
        tier = source.get("tier")
        credibility_score = source.get("credibility_score")
        if not tier or credibility_score is None:
            tier, credibility_score = classify_source_tier(
                url,
                citation_count=metadata.get("citation_count", 0),
                author_h_index=metadata.get("author_h_index"),
            )
        normalized.append(
            {
                "id": str(source.get("id") or ""),
                "url": url,
                "title": title,
                "authors": source.get("authors", []),
                "publication_date": source.get("publication_date") or "",
                "source_type": source.get("source_type") or "unknown",
                "domain": source.get("domain"),
                "tier": tier,
                "credibility_score": credibility_score,
                "citation_count": source.get("citation_count") or metadata.get("citation_count", 0),
                "content": source.get("content") or source.get("abstract") or source.get("parsed_text") or "",
                "parsed_text": source.get("parsed_text") or source.get("content") or source.get("abstract") or "",
                "metadata": metadata,
                "created_at": str(source.get("created_at") or source.get("fetched_at") or ""),
                "updated_at": str(source.get("updated_at") or ""),
            }
        )
    return normalized


def _dedupe_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped = []
    for source in sources:
        key = (source.get("url") or source.get("title") or "").lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(source)
    return deduped


def _source_preview(source: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": source.get("title"),
        "url": source.get("url"),
        "source_type": source.get("source_type"),
        "publication_date": source.get("publication_date"),
        "credibility_score": source.get("credibility_score"),
        "final_score": source.get("final_score", 0),
    }


def _resource_result(source: Dict[str, Any], insights: Dict[str, Any], query_terms: List[str]) -> Dict[str, Any]:
    metadata = source.get("metadata") or {}
    source_type = source.get("source_type") or "reference"
    return {
        "title": source.get("title") or "Untitled resource",
        "source_type": source_type,
        "category": _resource_category(source_type),
        "url": source.get("url"),
        "summary": _resource_summary(source),
        "why_relevant": _resource_relevance(source, insights, query_terms),
        "thumbnail_url": _thumbnail_from_metadata(metadata),
        "publication_date": source.get("publication_date") or "",
        "credibility_score": source.get("credibility_score", 0),
        "relevance_score": round(float(source.get("final_score", 0)), 3),
    }


def _resource_category(source_type: str) -> str:
    normalized = str(source_type or "").lower()
    if normalized in {"arxiv", "openalex", "semantic_scholar", "papers_with_code", "huggingface_papers"}:
        return "Research paper"
    if normalized == "github":
        return "GitHub repository"
    if normalized in {"rss_feed", "google_news", "gnews", "newsapi", "hackernews", "guardian", "nytimes", "gdelt", "mediacloud", "exa"}:
        return "Article / blog"
    return "Reference"


def _resource_summary(source: Dict[str, Any]) -> str:
    text = " ".join(
        str(part or "")
        for part in [source.get("content"), source.get("abstract"), source.get("parsed_text")]
    )
    cleaned = " ".join(text.split())
    if not cleaned:
        cleaned = str(source.get("title") or "")
    sentences = _split_summary_sentences(cleaned)
    summary = " ".join(sentences[:3]).strip()
    return summary[:520] or "The source did not provide a summary, but the title and metadata matched the brief."


def _resource_relevance(source: Dict[str, Any], insights: Dict[str, Any], query_terms: List[str]) -> str:
    text = " ".join(
        str(part or "")
        for part in [source.get("title"), source.get("content"), source.get("abstract"), source.get("parsed_text")]
    ).lower()
    matched_terms = [term for term in query_terms if str(term).lower() in text][:4]
    if matched_terms:
        return f"Matches brief terms: {', '.join(matched_terms)}."
    topics = insights.get("key_topics") or insights.get("technical_keywords") or []
    matched_topics = [topic for topic in topics if str(topic).lower() in text][:3]
    if matched_topics:
        return f"Supports extracted topic(s): {', '.join(matched_topics)}."
    category = _resource_category(source.get("source_type") or "")
    return f"Ranked as a relevant {category.lower()} based on source quality, recency, and overlap with the brief."


def _thumbnail_from_metadata(metadata: Dict[str, Any]) -> Optional[str]:
    for key in ("image_url", "socialimage", "thumbnail", "thumbnail_url", "og_image", "avatar_url"):
        value = metadata.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    return None


def _valid_result_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def _split_summary_sentences(text: str) -> List[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def _suggest_project_architecture(recommendations: List[Dict[str, Any]], insights: Dict[str, Any]) -> Dict[str, Any]:
    names = [rec.get("technology_name", "") for rec in recommendations]
    has_vector = any(name in {"pgvector", "Qdrant", "Pinecone", "Weaviate", "Milvus", "FAISS"} for name in names)
    has_agent = any(name in {"LangGraph", "LangChain"} for name in names) or any(
        "agent" in topic.lower() for topic in insights.get("key_topics", [])
    )
    has_model = any(name in {"OpenAI", "Anthropic Claude", "Google Gemini", "Meta Llama", "Mistral", "Cohere"} for name in names)

    layers = ["FastAPI backend", "PostgreSQL operational store", "source ingestion scheduler"]
    if has_vector:
        layers.append("citation-backed RAG retrieval layer")
    if has_model:
        layers.append("LLM provider abstraction with fallback routing")
    if has_agent:
        layers.append("bounded agent workflow layer")
    layers.append("dashboard and report export UI")

    return {
        "choice": "Hybrid research intelligence architecture",
        "layers": layers,
        "rationale": "The brief needs grounded recommendations, citations, scheduled source updates, and human-readable reports.",
    }


def _aggregate_risks(recommendations: List[Dict[str, Any]], insights: Dict[str, Any]) -> List[str]:
    risks = list(insights.get("risks", []))
    for recommendation in recommendations:
        risks.extend(recommendation.get("risks_tradeoffs", [])[:2])
    deduped = []
    seen = set()
    for risk in risks:
        key = str(risk).lower()
        if key not in seen:
            seen.add(key)
            deduped.append(str(risk))
    return deduped[:10]


def _aggregate_next_steps(recommendations: List[Dict[str, Any]]) -> List[str]:
    steps = [
        "Review the citations for each recommendation before procurement or implementation.",
        "Select one Adopt Now or Trial item for a small proof of concept.",
        "Define success metrics for retrieval quality, latency, cost, and citation precision.",
    ]
    for recommendation in recommendations[:3]:
        steps.extend(recommendation.get("next_steps", [])[:1])
    return steps[:8]
