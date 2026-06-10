import pytest
from pathlib import Path
from uuid import uuid4

from research_intelligence.brief_service import BriefIntelligenceService
from research_intelligence.store import IntelligenceStore


@pytest.mark.asyncio
async def test_upload_analyze_recommendation_flow_uses_cited_evidence(monkeypatch):
    store_path = Path(".pytest_cache") / f"brief-flow-{uuid4().hex}.json"
    store = IntelligenceStore(local_path=store_path, use_postgres=False)
    service = BriefIntelligenceService(store=store)

    async def fake_fetch_external_sources(self, query_terms):
        return [
            {
                "title": "Qdrant production RAG patterns",
                "url": "https://github.com/qdrant/qdrant",
                "source_type": "github",
                "content": "Qdrant is a vector database for RAG, semantic search, filtering, and production APIs.",
                "publication_date": "2026-03-01",
                "credibility_score": 85,
                "metadata": {"stars": 26000, "forks": 1900},
            },
            {
                "title": "RAGAS evaluation for retrieval augmented generation",
                "url": "https://docs.ragas.io",
                "source_type": "rss_feed",
                "content": "RAGAS provides RAG evaluation metrics for citation-backed retrieval systems.",
                "publication_date": "2026-02-01",
                "credibility_score": 70,
                "metadata": {},
            },
        ]

    monkeypatch.setattr(BriefIntelligenceService, "_fetch_external_sources", fake_fetch_external_sources)

    upload = await service.upload_brief(
        "project.md",
        b"We need to build a RAG dashboard using Qdrant, FastAPI, and citation-backed recommendations for an AI team.",
    )
    report = await service.analyze_brief(upload["brief_id"], refresh_sources=True)
    recommendations = service.get_recommendations(upload["brief_id"])

    assert report["evidence_sources_count"] == 2
    assert recommendations
    assert all(item["citations"] for item in recommendations)
    assert any(item["technology_name"] == "Qdrant" for item in recommendations)
