"""
Comprehensive test of all data ingestion sources
"""
import asyncio
from ingestion.source_orchestrator import SourceOrchestrator
from loguru import logger

async def test_all_sources():
    """Test each data source individually"""
    orchestrator = SourceOrchestrator()
    
    print("\n" + "=" * 70)
    print("🧪 MULTI-SOURCE INGESTION TEST")
    print("=" * 70)
    
    test_keywords = ["machine learning", "AI"]
    
    # Test 1: ArXiv (No API key needed)
    print("\n1️⃣  Testing ArXiv API...")
    try:
        arxiv_results = await orchestrator._fetch_arxiv(test_keywords)
        print(f"   ✅ ArXiv: Found {len(arxiv_results)} papers")
        if arxiv_results:
            print(f"   📄 Sample: {arxiv_results[0]['title'][:60]}...")
    except Exception as e:
        print(f"   ❌ ArXiv failed: {e}")
    
    # Test 2: OpenAlex (No API key needed, just email)
    print("\n2️⃣  Testing OpenAlex API...")
    try:
        openalex_results = await orchestrator._fetch_openalex(test_keywords)
        print(f"   ✅ OpenAlex: Found {len(openalex_results)} papers")
        if openalex_results:
            print(f"   📄 Sample: {openalex_results[0]['title'][:60]}...")
    except Exception as e:
        print(f"   ❌ OpenAlex failed: {e}")
    
    # Test 3: Semantic Scholar (requires API key)
    print("\n3️⃣  Testing Semantic Scholar API...")
    try:
        ss_results = await orchestrator._fetch_semantic_scholar(test_keywords)
        if not ss_results:
            print(f"   ⏭️  Semantic Scholar: Skipped (no API key configured)")
        else:
            print(f"   ✅ Semantic Scholar: Found {len(ss_results)} papers")
            if ss_results:
                print(f"   📄 Sample: {ss_results[0]['title'][:60]}...")
    except Exception as e:
        print(f"   ❌ Semantic Scholar failed: {e}")
    
    # Test 4: GNews
    print("\n4️⃣  Testing GNews API...")
    try:
        gnews_results = await orchestrator._fetch_gnews(test_keywords)
        print(f"   ✅ GNews: Found {len(gnews_results)} articles")
        if gnews_results:
            print(f"   📰 Sample: {gnews_results[0]['title'][:60]}...")
    except Exception as e:
        print(f"   ❌ GNews failed: {e}")
    
    # Test 5: NewsAPI
    print("\n5️⃣  Testing NewsAPI...")
    try:
        newsapi_results = await orchestrator._fetch_newsapi(test_keywords)
        print(f"   ✅ NewsAPI: Found {len(newsapi_results)} articles")
        if newsapi_results:
            print(f"   📰 Sample: {newsapi_results[0]['title'][:60]}...")
    except Exception as e:
        print(f"   ❌ NewsAPI failed: {e}")
    
    # Test 6: RSS Feeds
    print("\n6️⃣  Testing RSS Feeds...")
    try:
        rss_results = await orchestrator._fetch_rss(test_keywords)
        print(f"   ✅ RSS Feeds: Found {len(rss_results)} articles")
        if rss_results:
            print(f"   📰 Sample: {rss_results[0]['title'][:60]}...")
    except Exception as e:
        print(f"   ❌ RSS failed: {e}")
    
    # Test 7: Google News
    print("\n7️⃣  Testing Google News RSS...")
    try:
        gnews_rss_results = await orchestrator._fetch_google_news(test_keywords[:1])
        print(f"   ✅ Google News: Found {len(gnews_rss_results)} articles")
        if gnews_rss_results:
            print(f"   📰 Sample: {gnews_rss_results[0]['title'][:60]}...")
    except Exception as e:
        print(f"   ❌ Google News failed: {e}")
    
    # Test 8: GitHub
    print("\n8️⃣  Testing GitHub API...")
    try:
        github_results = await orchestrator._fetch_github(test_keywords)
        print(f"   ✅ GitHub: Found {len(github_results)} repositories")
        if github_results:
            print(f"   💻 Sample: {github_results[0]['title']}")
    except Exception as e:
        print(f"   ❌ GitHub failed: {e}")
    
    # Test 9: Hacker News
    print("\n9️⃣  Testing Hacker News API...")
    try:
        hn_results = await orchestrator._fetch_hackernews(test_keywords)
        print(f"   ✅ Hacker News: Found {len(hn_results)} stories")
        if hn_results:
            print(f"   💬 Sample: {hn_results[0]['title'][:60]}...")
    except Exception as e:
        print(f"   ❌ Hacker News failed: {e}")
    
    print("\n" + "=" * 70)
    print("✅ TEST COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_all_sources())
