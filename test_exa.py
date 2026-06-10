"""Test Exa.ai integration."""
import asyncio
from ingestion.sources.news_sources import ExaFetcher


async def test_exa():
    print("🧪 Testing Exa.ai Integration...\n")
    
    fetcher = ExaFetcher()
    
    # Test semantic search for RAG content
    results = await fetcher.search("RAG vector database techniques", num_results=5)
    
    print(f"✅ Fetched {len(results)} results from Exa.ai\n")
    
    for i, article in enumerate(results, 1):
        print(f"📄 Result {i}:")
        print(f"   Title: {article['title']}")
        print(f"   URL: {article['url']}")
        print(f"   Score: {article['metadata'].get('score', 'N/A')}")
        print(f"   Description: {article['description'][:100]}...")
        print()


if __name__ == "__main__":
    asyncio.run(test_exa())
