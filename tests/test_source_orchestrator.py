import sys
import types
from contextlib import contextmanager

import pytest

from ingestion.source_orchestrator import SourceOrchestrator


def test_resolve_sources_validates_and_filters_apify():
    orchestrator = SourceOrchestrator()

    assert "apify_google_news" not in orchestrator._resolve_sources(
        enable_apify=False,
        requested_sources=["google_news", "apify_google_news"],
    )
    assert orchestrator._resolve_sources(
        enable_apify=True,
        requested_sources=["google_news", "apify_google_news"],
    ) == ["apify_google_news", "google_news"]

    with pytest.raises(ValueError, match="Unsupported source ids"):
        orchestrator._resolve_sources(enable_apify=False, requested_sources=["nope"])


def test_normalize_and_deduplicate_documents():
    orchestrator = SourceOrchestrator()
    docs = [
        {
            "title": " Same Title ",
            "content": "alpha",
            "authors": ["Author"],
            "publication_date": "2025-01-01",
            "url": "",
            "source_type": "rss_feed",
            "metadata": {},
        },
        {
            "title": "Same Title",
            "content": "beta",
            "authors": ["Author"],
            "publication_date": "2025-01-01",
            "url": "",
            "source_type": "rss_feed",
            "metadata": {},
        },
        {
            "title": "Arxiv Item",
            "abstract": "paper",
            "authors": ["Researcher"],
            "publication_date": "2024-02-03",
            "url": "https://arxiv.org/abs/1234.5678",
            "source_type": "arxiv",
            "metadata": {"citation_count": 50},
        },
    ]

    normalized = orchestrator._normalize_all(docs)
    deduped = orchestrator._deduplicate(normalized)

    assert normalized[0]["url"].startswith("urn:rss_feed:")
    assert normalized[2]["tier"] == "tier_1"
    assert normalized[2]["credibility_score"] >= 10
    assert len(deduped) == 2


@pytest.mark.asyncio
async def test_fetch_all_sources_honors_requested_allowlist(monkeypatch):
    orchestrator = SourceOrchestrator()

    async def fake_google_news_search(query: str, lang: str = "en", country: str = "US"):
        return [
            {
                "title": f"Result for {query}",
                "content": "body",
                "authors": ["source"],
                "publication_date": "2025-01-01",
                "url": f"https://example.com/{query}",
                "source_type": "google_news",
                "metadata": {},
            }
        ]

    monkeypatch.setattr(orchestrator.google_news, "search", fake_google_news_search)

    documents = await orchestrator.fetch_all_sources(
        keywords=["RAG"],
        sources=["google_news"],
        enable_apify=False,
    )

    assert len(documents) == 1
    assert documents[0]["source_type"] == "google_news"
    assert documents[0]["title"] == "Result for RAG"


def test_persist_documents_upserts_and_records_fetch_logs(monkeypatch):
    orchestrator = SourceOrchestrator()
    executed = []
    source_insert_results = iter([True, False])

    class FakeResult:
        def __init__(self, scalar_value=None):
            self._scalar_value = scalar_value

        def scalar(self):
            return self._scalar_value

    class FakeDB:
        def execute(self, query, params=None):
            sql = str(query)
            executed.append((sql, params))
            if "INSERT INTO sources" in sql:
                return FakeResult(next(source_insert_results))
            return FakeResult()

        def commit(self):
            executed.append(("COMMIT", None))

    @contextmanager
    def fake_get_db_context():
        yield FakeDB()

    fake_database_connection = types.SimpleNamespace(get_db_context=fake_get_db_context)
    monkeypatch.setitem(sys.modules, "database.connection", fake_database_connection)

    result = orchestrator.persist_documents(
        documents=[
            {
                "url": "https://example.com/a",
                "title": "A",
                "authors": ["one"],
                "publication_date": "2025-01-01",
                "source_type": "google_news",
                "tier": "tier_2",
                "credibility_score": 5,
                "metadata": {"citation_count": 0},
            },
            {
                "url": "https://example.com/b",
                "title": "B",
                "authors": ["two"],
                "publication_date": "2025-01-02",
                "source_type": "google_news",
                "tier": "tier_2",
                "credibility_score": 5,
                "metadata": {"citation_count": 0},
            },
        ],
        keywords=["RAG"],
    )

    assert result == {"items_new": 1, "items_updated": 1}
    assert any("INSERT INTO fetch_logs" in sql for sql, _ in executed if sql != "COMMIT")
    assert executed[-1][0] == "COMMIT"
