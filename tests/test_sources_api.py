from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers import sources as sources_router


def build_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(sources_router.router, prefix="/api/v1")
    return TestClient(app)


def test_sources_status_route_returns_configuration():
    client = build_test_client()

    response = client.get("/api/v1/sources/status")

    assert response.status_code == 200
    payload = response.json()
    assert "research_sources" in payload
    assert "known_source_ids" in payload


def test_sources_fetch_route_uses_orchestrator(monkeypatch):
    class FakeOrchestrator:
        async def fetch_and_store(self, keywords=None, enable_apify=False, sources=None):
            assert keywords == ["RAG"]
            assert enable_apify is False
            assert sources == ["google_news"]
            return {
                "items_fetched": 3,
                "items_new": 2,
                "items_updated": 1,
                "sources_used": ["google_news"],
            }

    monkeypatch.setattr(sources_router, "SourceOrchestrator", FakeOrchestrator)
    client = build_test_client()

    response = client.post(
        "/api/v1/sources/fetch",
        json={"keywords": ["RAG"], "sources": ["google_news"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["documents_fetched"] == 3
    assert payload["sources_used"] == ["google_news"]


def test_sources_fetch_route_rejects_unknown_sources():
    client = build_test_client()

    response = client.post("/api/v1/sources/fetch", json={"sources": ["unknown_source"]})

    assert response.status_code == 422
    assert "Unsupported sources" in response.text


def test_sources_stats_route_returns_mocked_stats(monkeypatch):
    class FakeOrchestrator:
        def get_fetch_stats(self):
            return {"recent_runs": [{"source_type": "google_news"}], "by_source": []}

    monkeypatch.setattr(sources_router, "SourceOrchestrator", FakeOrchestrator)
    client = build_test_client()

    response = client.get("/api/v1/sources/stats")

    assert response.status_code == 200
    assert response.json()["recent_runs"][0]["source_type"] == "google_news"
