from config import Settings


def test_debug_coercion_handles_release_strings():
    settings = Settings(debug="release")
    assert settings.debug is False


def test_settings_expose_multi_source_defaults():
    settings = Settings()
    assert "https://openai.com/blog/rss.xml" in settings.rss_feeds
    assert "rag" in settings.github_topics
    assert "RAG" in settings.news_keywords


def test_settings_parse_list_properties():
    settings = Settings(allowed_origins="https://a.test, https://b.test", allowed_file_types="pdf, html, txt")
    assert settings.allowed_origins_list == ["https://a.test", "https://b.test"]
    assert settings.allowed_file_types_list == ["pdf", "html", "txt"]
