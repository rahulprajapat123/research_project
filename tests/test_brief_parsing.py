import pytest

from research_intelligence.parsing import BriefParsingError, extract_brief_insights, parse_brief_file


def test_parse_markdown_brief_and_extract_insights():
    content = b"""
    # Research Dashboard
    We need to build a RAG market intelligence dashboard for a technical team.
    It must use FastAPI, PostgreSQL, pgvector, and daily team email.
    The system should provide citation-backed recommendations under 3 seconds.
    Target users are engineering leaders and AI developers.
    """

    parsed = parse_brief_file("brief.md", content, max_size_mb=1)
    insights = extract_brief_insights(parsed.content_text)

    assert parsed.file_type == "md"
    assert "RAG" in insights["stack"]
    assert "FastAPI" in insights["stack"]
    assert insights["key_topics"]
    assert insights["technical_requirements"]


def test_reject_unsupported_brief_file_type():
    with pytest.raises(BriefParsingError):
        parse_brief_file("brief.exe", b"not allowed", max_size_mb=1)

