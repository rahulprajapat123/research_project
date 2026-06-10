from research_intelligence.scoring import (
    build_technology_recommendations,
    keyword_similarity,
    rank_source_documents,
)


def test_keyword_similarity_rewards_phrase_and_token_overlap():
    score = keyword_similarity(["vector database", "RAG"], "Qdrant is a vector database for RAG systems.")

    assert score > 0.7


def test_recommendation_scoring_requires_cited_sources():
    documents = [
        {
            "title": "Qdrant RAG implementation patterns",
            "url": "https://github.com/qdrant/qdrant",
            "source_type": "github",
            "content": "Qdrant vector database supports RAG retrieval, filtering, and production implementation.",
            "publication_date": "2026-01-10",
            "credibility_score": 80,
            "metadata": {"stars": 25000, "forks": 1800},
        }
    ]
    ranked = rank_source_documents(documents, ["RAG", "vector database", "Qdrant"])
    recommendations = build_technology_recommendations(
        ranked,
        {"domain": "enterprise knowledge", "key_topics": ["RAG", "vector database"]},
        ["RAG", "vector database", "Qdrant"],
    )

    assert ranked[0]["final_score"] > 0.5
    assert any(rec["technology_name"] == "Qdrant" for rec in recommendations)
    qdrant = next(rec for rec in recommendations if rec["technology_name"] == "Qdrant")
    assert qdrant["citations"][0]["url"] == "https://github.com/qdrant/qdrant"

