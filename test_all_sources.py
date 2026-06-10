"""
Test script to verify all data sources are working and fetching data correctly.
"""
import asyncio
from typing import Dict, Any, List
from loguru import logger

from config import get_settings
from ingestion.sources.research_sources import (
    ArxivFetcher,
    SemanticScholarFetcher,
    OpenAlexFetcher,
    HuggingFacePapersFetcher,
    PapersWithCodeFetcher,
)
from ingestion.sources.news_sources import (
    GNewsFetcher,
    NewsAPIFetcher,
    RSSFeedFetcher,
    MediaCloudFetcher,
    GDELTFetcher,
    GuardianAPIFetcher,
    NYTimesAPIFetcher,
)
from ingestion.sources.developer_sources import (
    GitHubFetcher,
    HackerNewsFetcher,
    GitHubAwesomeListsFetcher,
)

settings = get_settings()

# Configure logger
logger.add("logs/test_sources_{time}.log", rotation="10 MB")


async def test_source(name: str, fetch_func, *args, **kwargs) -> Dict[str, Any]:
    """Test a single data source."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    
    try:
        results = await fetch_func(*args, **kwargs)
        count = len(results)
        
        if count > 0:
            print(f"✅ SUCCESS: Fetched {count} items")
            # Show first result as sample
            if results:
                first = results[0]
                print(f"   Sample title: {first.get('title', 'N/A')[:80]}")
                print(f"   Source type: {first.get('source_type', 'N/A')}")
                print(f"   URL: {first.get('url', 'N/A')[:80]}")
        else:
            print(f"⚠️  WARNING: No results returned (may need API key or query adjustment)")
        
        return {
            "name": name,
            "status": "success",
            "count": count,
            "error": None
        }
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        logger.error(f"Error testing {name}: {str(e)}")
        return {
            "name": name,
            "status": "error",
            "count": 0,
            "error": str(e)
        }


async def main():
    """Run tests for all data sources."""
    print("\n" + "="*60)
    print("🧪 TESTING ALL DATA SOURCES")
    print("="*60)
    
    test_keywords = ["artificial intelligence", "machine learning"]
    results: List[Dict[str, Any]] = []
    
    # Academic Research Sources
    print("\n\n📚 ACADEMIC RESEARCH SOURCES")
    print("="*60)
    
    results.append(await test_source(
        "arXiv",
        ArxivFetcher().search,
        keywords=["RAG", "retrieval augmented generation"],
        max_results=5
    ))
    
    if settings.semantic_scholar_api_key:
        results.append(await test_source(
            "Semantic Scholar",
            SemanticScholarFetcher().search,
            query="retrieval augmented generation",
            limit=5
        ))
    else:
        print("\n⏭️  Skipping Semantic Scholar (no API key)")
        results.append({"name": "Semantic Scholar", "status": "skipped", "count": 0, "error": "No API key"})
    
    results.append(await test_source(
        "OpenAlex",
        OpenAlexFetcher().search,
        query="large language models",
        limit=5
    ))
    
    if settings.huggingface_token:
        results.append(await test_source(
            "Hugging Face Papers",
            HuggingFacePapersFetcher().fetch_daily_papers,
            limit=5
        ))
    else:
        print("\n⏭️  Skipping Hugging Face Papers (no token)")
        results.append({"name": "Hugging Face Papers", "status": "skipped", "count": 0, "error": "No token"})
    
    results.append(await test_source(
        "Papers with Code",
        PapersWithCodeFetcher().get_trending_papers,
        limit=5
    ))
    
    # News Sources
    print("\n\n📰 NEWS SOURCES")
    print("="*60)
    
    if settings.gnews_api_key:
        results.append(await test_source(
            "GNews",
            GNewsFetcher().search,
            query="artificial intelligence",
            max_articles=5
        ))
    else:
        print("\n⏭️  Skipping GNews (no API key)")
        results.append({"name": "GNews", "status": "skipped", "count": 0, "error": "No API key"})
    
    if settings.newsapi_key:
        results.append(await test_source(
            "NewsAPI",
            NewsAPIFetcher().search,
            query="machine learning",
            max_articles=5
        ))
    else:
        print("\n⏭️  Skipping NewsAPI (no API key)")
        results.append({"name": "NewsAPI", "status": "skipped", "count": 0, "error": "No API key"})
    
    results.append(await test_source(
        "RSS Feeds",
        RSSFeedFetcher().fetch_feed,
        feed_url="https://huggingface.co/blog/feed.xml"
    ))
    
    if settings.mediacloud_api_key:
        results.append(await test_source(
            "Media Cloud",
            MediaCloudFetcher().search,
            query="artificial intelligence",
            max_articles=5
        ))
    else:
        print("\n⏭️  Skipping Media Cloud (no API key)")
        results.append({"name": "Media Cloud", "status": "skipped", "count": 0, "error": "No API key"})
    
    results.append(await test_source(
        "GDELT",
        GDELTFetcher().search,
        query="artificial intelligence",
        max_records=5,
        time_span="7d"
    ))
    
    if settings.guardian_api_key:
        results.append(await test_source(
            "The Guardian",
            GuardianAPIFetcher().search,
            query="artificial intelligence",
            page_size=5
        ))
    else:
        print("\n⏭️  Skipping The Guardian (no API key)")
        results.append({"name": "The Guardian", "status": "skipped", "count": 0, "error": "No API key"})
    
    if settings.nytimes_api_key:
        results.append(await test_source(
            "New York Times",
            NYTimesAPIFetcher().search,
            query="artificial intelligence",
            page_size=5
        ))
    else:
        print("\n⏭️  Skipping New York Times (no API key)")
        results.append({"name": "New York Times", "status": "skipped", "count": 0, "error": "No API key"})
    
    # Developer Sources
    print("\n\n👨‍💻 DEVELOPER PLATFORM SOURCES")
    print("="*60)
    
    if settings.github_token:
        results.append(await test_source(
            "GitHub Repositories",
            GitHubFetcher().search_repositories,
            topics=["rag", "retrieval-augmented-generation"],
            max_results=5
        ))
        
        results.append(await test_source(
            "GitHub Awesome Lists",
            GitHubAwesomeListsFetcher().fetch_awesome_lists,
            repo_list=["Wrenbjor/awesome-llm"]
        ))
    else:
        print("\n⏭️  Skipping GitHub sources (no token)")
        results.append({"name": "GitHub Repositories", "status": "skipped", "count": 0, "error": "No token"})
        results.append({"name": "GitHub Awesome Lists", "status": "skipped", "count": 0, "error": "No token"})
    
    results.append(await test_source(
        "Hacker News",
        HackerNewsFetcher().search,
        keywords=["artificial intelligence"],
        days_back=7
    ))
    
    # Summary
    print("\n\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    successful = [r for r in results if r["status"] == "success" and r["count"] > 0]
    failed = [r for r in results if r["status"] == "error"]
    skipped = [r for r in results if r["status"] == "skipped"]
    empty = [r for r in results if r["status"] == "success" and r["count"] == 0]
    
    print(f"\n✅ Successful: {len(successful)}/{len(results)}")
    for r in successful:
        print(f"   - {r['name']}: {r['count']} items")
    
    if empty:
        print(f"\n⚠️  Empty Results: {len(empty)}")
        for r in empty:
            print(f"   - {r['name']}")
    
    if skipped:
        print(f"\n⏭️  Skipped: {len(skipped)} (missing API keys)")
        for r in skipped:
            print(f"   - {r['name']}: {r['error']}")
    
    if failed:
        print(f"\n❌ Failed: {len(failed)}")
        for r in failed:
            print(f"   - {r['name']}: {r['error']}")
    
    total_items = sum(r["count"] for r in results)
    print(f"\n📈 Total items fetched: {total_items}")
    
    # Recommendations
    print("\n\n💡 RECOMMENDATIONS")
    print("="*60)
    
    if not settings.semantic_scholar_api_key:
        print("• Get Semantic Scholar API key: https://www.semanticscholar.org/product/api")
    
    if not settings.huggingface_token:
        print("• Get Hugging Face token: https://huggingface.co/settings/tokens")
    
    if not settings.github_token:
        print("• Get GitHub token: https://github.com/settings/tokens")
    
    if not settings.mediacloud_api_key:
        print("• Get Media Cloud API key: https://mediacloud.org/")
    
    if not settings.guardian_api_key:
        print("• Get Guardian API key: https://open-platform.theguardian.com/access/")
    
    if not settings.nytimes_api_key:
        print("• Get NY Times API key: https://developer.nytimes.com/get-started")
    
    print("\n✨ Testing complete!\n")


if __name__ == "__main__":
    asyncio.run(main())
