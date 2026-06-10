from research_intelligence.emailer import build_daily_email_html, build_daily_email_markdown


def test_daily_email_rendering_includes_updates_and_actions():
    report = {
        "subject": "Daily AI & RAG Intelligence Brief - 2026-05-31",
        "summary": "Two prioritized updates.",
        "top_updates": [
            {
                "title": "New RAG benchmark",
                "url": "https://example.com/rag",
                "category_tags": ["RAG", "Research"],
                "impact_score": 0.82,
                "why_it_matters": "High-confidence retrieval signal.",
                "recommended_action": "Review with the team.",
            }
        ],
        "worth_exploring": [],
        "emerging_signals": [],
        "ignore_for_now": [],
    }

    html = build_daily_email_html(report)
    markdown = build_daily_email_markdown(report)

    assert "New RAG benchmark" in html
    assert "Review with the team" in html
    assert "[New RAG benchmark](https://example.com/rag)" in markdown

