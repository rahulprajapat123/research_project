"""Test configuration loading"""
from config import get_settings

settings = get_settings()

print("=" * 60)
print("CONFIGURATION TEST")
print("=" * 60)

print(f"\n🔧 App Configuration:")
print(f"  App Name: {settings.app_name}")
print(f"  Environment: {settings.environment}")
print(f"  Debug Mode: {settings.debug}")

print(f"\n🔑 API Keys Status:")
print(f"  ✓ GNews API Key: {'Configured ✅' if settings.gnews_api_key else 'Missing ❌'}")
print(f"  ✓ NewsAPI Key: {'Configured ✅' if settings.newsapi_key else 'Missing ❌'}")
print(f"  ✓ GitHub Token: {'Configured ✅' if settings.github_token else 'Missing ❌'}")
print(f"  ✓ Apify Token: {'Configured ✅' if settings.apify_api_token else 'Missing ❌'}")
print(f"  ✓ Semantic Scholar: {'Configured ✅' if settings.semantic_scholar_api_key else 'Missing ❌ (Expected)'}")
print(f"  ✓ OpenAlex Email: {settings.openalex_contact_email}")

print(f"\n⚙️  Fetch Configuration:")
print(f"  Max Papers/Source: {settings.max_papers_per_source}")
print(f"  Max News/Source: {settings.max_news_articles_per_source}")
print(f"  Max GitHub Repos: {settings.max_github_repos}")
print(f"  Fetch Interval: Every {settings.fetch_interval_hours} hours")
print(f"  Min Publication Year: {settings.min_publication_year}")

print(f"\n📊 RSS Feeds: {len(settings.rss_feeds)} configured")
print(f"📊 News Keywords: {len(settings.news_keywords)} configured")
print(f"📊 GitHub Topics: {len(settings.github_topics)} configured")

print("\n" + "=" * 60)
