"""Quick test of fixed sources"""
import asyncio
from config import get_settings
from ingestion.sources.news_sources import NYTimesAPIFetcher
from ingestion.sources.developer_sources import GitHubAwesomeListsFetcher

settings = get_settings()

async def test_nytimes():
    print("\nTesting NYTimes API...")
    fetcher = NYTimesAPIFetcher()
    results = await fetcher.search("artificial intelligence")
    print(f"NYTimes: {len(results)} articles fetched")
    if results:
        print(f"Sample: {results[0]['title'][:80]}")
    return len(results)

async def test_awesome_lists():
    print("\nTesting GitHub Awesome Lists...")
    fetcher = GitHubAwesomeListsFetcher()
    results = await fetcher.fetch_awesome_lists(["Hannibal046/Awesome-LLM"])
    print(f"Awesome Lists: {len(results)} lists fetched")
    if results:
        print(f"Sample: {results[0]['title'][:80]}")
        print(f"Links found: {results[0]['metadata'].get('total_links', 0)}")
    return len(results)

async def main():
    print("="*60)
    print("Testing Fixed Sources")
    print("="*60)
    
    nyt_count = await test_nytimes()
    awesome_count = await test_awesome_lists()
    
    print("\n" + "="*60)
    print("Results:")
    print(f"  NYTimes: {'OK' if nyt_count > 0 else 'FAILED'} ({nyt_count} items)")
    print(f"  Awesome Lists: {'OK' if awesome_count > 0 else 'FAILED'} ({awesome_count} items)")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
