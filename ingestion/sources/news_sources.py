"""
News and RSS source integrations.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import feedparser
import httpx
from loguru import logger

from config import get_settings

settings = get_settings()


class GNewsFetcher:
    BASE_URL = "https://gnews.io/api/v4/search"

    def __init__(self) -> None:
        self.api_key = settings.gnews_api_key

    async def search(
        self,
        query: str,
        lang: str = "en",
        country: str = "us",
        max_articles: int = 100,
    ) -> List[Dict[str, Any]]:
        if not self.api_key:
            logger.info("GNews API key not configured, skipping")
            return []

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "q": query,
                        "lang": lang,
                        "country": country,
                        "max": max_articles,
                        "apikey": self.api_key,
                    },
                )
                response.raise_for_status()
        except Exception as exc:
            logger.warning(f"GNews fetch failed for '{query}': {exc}")
            return []

        payload = response.json()
        return [
            {
                "title": article.get("title", ""),
                "content": "\n\n".join(
                    part for part in [article.get("description", ""), article.get("content", "")] if part
                ),
                "authors": [article.get("source", {}).get("name", "Unknown")],
                "publication_date": (article.get("publishedAt") or "")[:10],
                "url": article.get("url", ""),
                "source_type": "gnews",
                "metadata": {
                    "source_name": article.get("source", {}).get("name", ""),
                    "image_url": article.get("image", ""),
                },
            }
            for article in payload.get("articles", [])
        ]


class NewsAPIFetcher:
    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self) -> None:
        self.api_key = settings.newsapi_key

    async def search(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        from_date: Optional[str] = None,
        max_articles: int = 100,
    ) -> List[Dict[str, Any]]:
        if not self.api_key:
            logger.info("NewsAPI key not configured, skipping")
            return []

        if from_date is None:
            from_date = (datetime.utcnow() - timedelta(days=settings.news_lookback_days)).strftime("%Y-%m-%d")

        if sources is None:
            sources = ["techcrunch", "wired", "ars-technica", "the-verge"]

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "q": query,
                        "sources": ",".join(sources),
                        "from": from_date,
                        "sortBy": "publishedAt",
                        "pageSize": min(max_articles, 100),
                        "apiKey": self.api_key,
                    },
                )
                response.raise_for_status()
        except Exception as exc:
            logger.warning(f"NewsAPI fetch failed for '{query}': {exc}")
            return []

        payload = response.json()
        return [
            {
                "title": article.get("title", ""),
                "content": "\n\n".join(
                    part for part in [article.get("description", ""), article.get("content", "")] if part
                ),
                "authors": [article.get("author") or article.get("source", {}).get("name", "Unknown")],
                "publication_date": (article.get("publishedAt") or "")[:10],
                "url": article.get("url", ""),
                "source_type": "newsapi",
                "metadata": {
                    "source_name": article.get("source", {}).get("name", ""),
                    "image_url": article.get("urlToImage", ""),
                },
            }
            for article in payload.get("articles", [])
        ]


class RSSFeedFetcher:
    async def fetch_feed(self, feed_url: str) -> List[Dict[str, Any]]:
        try:
            loop = asyncio.get_running_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, feed_url)
        except Exception as exc:
            logger.warning(f"RSS feed fetch failed for {feed_url}: {exc}")
            return []

        articles: List[Dict[str, Any]] = []
        for entry in getattr(feed, "entries", [])[:50]:
            try:
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                publication_date = (
                    datetime(*published[:6]).date().isoformat()
                    if published
                    else datetime.utcnow().date().isoformat()
                )
                if hasattr(entry, "content") and entry.content:
                    content = entry.content[0].get("value", "")
                else:
                    content = entry.get("summary", "") or entry.get("description", "")

                articles.append(
                    {
                        "title": entry.get("title", ""),
                        "content": content,
                        "authors": [entry.get("author") or feed.feed.get("title", "Unknown")],
                        "publication_date": publication_date,
                        "url": entry.get("link", ""),
                        "source_type": "rss_feed",
                        "metadata": {
                            "feed_title": feed.feed.get("title", ""),
                            "feed_url": feed_url,
                            "tags": [tag.get("term", "") for tag in entry.get("tags", []) if tag.get("term")],
                        },
                    }
                )
            except Exception as exc:
                logger.debug(f"Skipping malformed RSS entry from {feed_url}: {exc}")

        return articles

    async def fetch_all_feeds(self, feed_urls: List[str]) -> List[Dict[str, Any]]:
        results = await asyncio.gather(*(self.fetch_feed(url) for url in feed_urls), return_exceptions=True)
        articles: List[Dict[str, Any]] = []
        for result in results:
            if isinstance(result, list):
                articles.extend(result)
        logger.info(f"Fetched {len(articles)} articles across {len(feed_urls)} RSS feeds")
        return articles


class GoogleNewsFetcher:
    BASE_URL = "https://news.google.com/rss/search"

    async def search(self, query: str, lang: str = "en", country: str = "US") -> List[Dict[str, Any]]:
        rss_url = (
            f"{self.BASE_URL}?q={quote_plus(query)}&hl={lang}&gl={country}&ceid={country}:{lang}"
        )
        articles = await RSSFeedFetcher().fetch_feed(rss_url)
        for article in articles:
            article["source_type"] = "google_news"
            article.setdefault("metadata", {})["query"] = query
        return articles


class MediaCloudFetcher:
    """
    Fetch news articles from Media Cloud - a research-grade news aggregator.
    Open-source platform tracking global news ecosystems with historical data.
    """
    BASE_URL = "https://api.mediacloud.org/api/v2"

    def __init__(self) -> None:
        self.api_key = settings.mediacloud_api_key

    async def search(
        self,
        query: str,
        collections: Optional[List[int]] = None,
        start_date: Optional[str] = None,
        max_articles: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search Media Cloud for articles matching query.
        
        Args:
            query: Solr query string
            collections: List of collection IDs (e.g., [34412234] for top US news)
            start_date: Start date in YYYY-MM-DD format
            max_articles: Maximum number of articles to return
        """
        if not self.api_key:
            logger.info("Media Cloud API key not configured, skipping")
            return []

        if start_date is None:
            start_date = (datetime.utcnow() - timedelta(days=settings.news_lookback_days)).strftime("%Y-%m-%d")

        if collections is None:
            # Default to top US online news collection
            collections = [34412234]

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    f"{self.BASE_URL}/stories_public/list",
                    params={
                        "q": query,
                        "fq": f"publish_date:[{start_date}T00:00:00Z TO NOW]",
                        "rows": max_articles,
                        "key": self.api_key,
                    },
                )
                response.raise_for_status()
        except Exception as exc:
            logger.warning(f"Media Cloud fetch failed for '{query}': {exc}")
            return []

        payload = response.json()
        articles: List[Dict[str, Any]] = []
        for story in payload.get("stories", []):
            articles.append(
                {
                    "title": story.get("title", ""),
                    "content": story.get("description", ""),
                    "authors": [story.get("media_name", "Unknown")],
                    "publication_date": (story.get("publish_date") or "")[:10],
                    "url": story.get("url", ""),
                    "source_type": "mediacloud",
                    "metadata": {
                        "stories_id": story.get("stories_id"),
                        "media_id": story.get("media_id"),
                        "media_name": story.get("media_name"),
                        "language": story.get("language"),
                        "inlink_count": story.get("inlink_count", 0),
                    },
                }
            )

        logger.info(f"Fetched {len(articles)} articles from Media Cloud for '{query}'")
        return articles


class GDELTFetcher:
    """
    Fetch news from GDELT (Global Database of Events, Location and Tone).
    Monitors world news in 100+ languages, updates every 15 minutes, historical data to 1979.
    """
    BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

    async def search(
        self,
        query: str,
        mode: str = "artlist",
        max_records: int = 250,
        time_span: str = "30d",
    ) -> List[Dict[str, Any]]:
        """
        Search GDELT for articles.
        
        Args:
            query: Search query
            mode: "artlist" for article list
            max_records: Maximum number of records (max 250)
            time_span: Time span (e.g., "30d", "7d", "24h")
        """
        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "query": query,
                        "mode": mode,
                        "maxrecords": min(max_records, 250),
                        "timespan": time_span,
                        "format": "json",
                    },
                )
                response.raise_for_status()
        except Exception as exc:
            logger.warning(f"GDELT fetch failed for '{query}': {exc}")
            return []

        payload = response.json()
        articles: List[Dict[str, Any]] = []
        for article in payload.get("articles", []):
            # Parse GDELT date format (YYYYMMDDHHMMSS)
            date_str = article.get("seendate", "")
            try:
                publication_date = datetime.strptime(date_str[:8], "%Y%m%d").date().isoformat() if date_str else ""
            except Exception:
                publication_date = datetime.utcnow().date().isoformat()

            articles.append(
                {
                    "title": article.get("title", ""),
                    "content": article.get("title", ""),  # GDELT doesn't provide full content
                    "authors": [article.get("domain", "Unknown")],
                    "publication_date": publication_date,
                    "url": article.get("url", ""),
                    "source_type": "gdelt",
                    "metadata": {
                        "domain": article.get("domain"),
                        "language": article.get("language"),
                        "seendate": article.get("seendate"),
                        "socialimage": article.get("socialimage"),
                        "tone": article.get("tone"),
                    },
                }
            )

        logger.info(f"Fetched {len(articles)} articles from GDELT for '{query}'")
        return articles


class GuardianAPIFetcher:
    """
    Fetch articles from The Guardian API.
    High-quality historical archive with free developer API for non-commercial use.
    """
    BASE_URL = "https://content.guardianapis.com/search"

    def __init__(self) -> None:
        self.api_key = settings.guardian_api_key

    async def search(
        self,
        query: str,
        from_date: Optional[str] = None,
        page_size: int = 50,
        show_fields: str = "headline,byline,body",
    ) -> List[Dict[str, Any]]:
        """
        Search The Guardian for articles.
        
        Args:
            query: Search query
            from_date: Start date in YYYY-MM-DD format
            page_size: Results per page (max 50)
            show_fields: Fields to include in response
        """
        if not self.api_key:
            logger.info("Guardian API key not configured, skipping")
            return []

        if from_date is None:
            from_date = (datetime.utcnow() - timedelta(days=settings.news_lookback_days)).strftime("%Y-%m-%d")

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "q": query,
                        "from-date": from_date,
                        "page-size": min(page_size, 50),
                        "show-fields": show_fields,
                        "api-key": self.api_key,
                    },
                )
                response.raise_for_status()
        except Exception as exc:
            logger.warning(f"Guardian API fetch failed for '{query}': {exc}")
            return []

        payload = response.json()
        articles: List[Dict[str, Any]] = []
        for result in payload.get("response", {}).get("results", []):
            fields = result.get("fields", {})
            articles.append(
                {
                    "title": fields.get("headline") or result.get("webTitle", ""),
                    "content": fields.get("body", ""),
                    "authors": [fields.get("byline", "The Guardian")],
                    "publication_date": (result.get("webPublicationDate") or "")[:10],
                    "url": result.get("webUrl", ""),
                    "source_type": "guardian",
                    "metadata": {
                        "section_id": result.get("sectionId"),
                        "section_name": result.get("sectionName"),
                        "article_type": result.get("type"),
                        "pillar_name": result.get("pillarName"),
                    },
                }
            )

        logger.info(f"Fetched {len(articles)} articles from The Guardian for '{query}'")
        return articles


class NYTimesAPIFetcher:
    """
    Fetch articles from The New York Times API.
    High-quality historical archive with free developer API for non-commercial use.
    """
    BASE_URL = "https://api.nytimes.com/svc/search/v2/articlesearch.json"

    def __init__(self) -> None:
        self.api_key = settings.nytimes_api_key

    async def search(
        self,
        query: str,
        begin_date: Optional[str] = None,
        page: int = 0,
        page_size: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search The New York Times for articles.
        
        Args:
            query: Search query
            begin_date: Start date in YYYYMMDD format
            page: Page number (0-indexed)
            page_size: Results per page (max 10)
        """
        if not self.api_key:
            logger.info("NYTimes API key not configured, skipping")
            return []

        if begin_date is None:
            begin_date = (datetime.utcnow() - timedelta(days=settings.news_lookback_days)).strftime("%Y%m%d")

        articles: List[Dict[str, Any]] = []
        
        # Fetch multiple pages to get more results (max 10 results per page from NYT)
        max_pages = min(10, settings.max_news_articles_per_source // 10)
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for page_num in range(max_pages):
                try:
                    response = await client.get(
                        self.BASE_URL,
                        params={
                            "q": query,
                            "begin_date": begin_date,
                            "page": page_num,
                            "api-key": self.api_key,
                        },
                    )
                    response.raise_for_status()
                    
                    payload = response.json()
                    docs = payload.get("response", {}).get("docs", [])
                    
                    if not docs:
                        break
                    
                    for doc in docs:
                        authors = [
                            person.get("firstname", "") + " " + person.get("lastname", "")
                            for person in doc.get("byline", {}).get("person", [])
                        ]
                        if not authors:
                            authors = ["The New York Times"]

                        articles.append(
                            {
                                "title": doc.get("headline", {}).get("main", ""),
                                "content": doc.get("abstract", "") or doc.get("lead_paragraph", ""),
                                "authors": authors,
                                "publication_date": (doc.get("pub_date") or "")[:10],
                                "url": doc.get("web_url", ""),
                                "source_type": "nytimes",
                                "metadata": {
                                    "section_name": doc.get("section_name"),
                                    "news_desk": doc.get("news_desk"),
                                    "document_type": doc.get("document_type"),
                                    "word_count": doc.get("word_count", 0),
                                    "keywords": [
                                        kw.get("value", "") 
                                        for kw in doc.get("keywords", [])
                                    ],
                                },
                            }
                        )
                    
                    # Rate limiting: NYTimes allows 10 requests/minute
                    await asyncio.sleep(6)
                    
                except Exception as exc:
                    logger.warning(f"NYTimes API fetch failed for '{query}' page {page_num}: {exc}")
                    break

        logger.info(f"Fetched {len(articles)} articles from The New York Times for '{query}'")
        return articles


class ExaFetcher:
    """Fetch high-quality research content using Exa.ai semantic search."""
    
    BASE_URL = "https://api.exa.ai/search"
    CONTENTS_URL = "https://api.exa.ai/contents"
    
    def __init__(self) -> None:
        self.api_key = settings.exa_api_key
    
    async def search(
        self,
        query: str,
        num_results: int = 10,
        use_autoprompt: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search for RAG-related content using Exa's semantic search.
        
        Args:
            query: Search query (e.g., "RAG techniques", "vector databases")
            num_results: Number of results to return (default 10)
            use_autoprompt: Use Exa's autoprompt for better results
        
        Returns:
            List of articles with title, url, published_date, and content
        """
        if not self.api_key:
            logger.info("Exa API key not configured, skipping")
            return []
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Step 1: Search for relevant URLs
                search_response = await client.post(
                    self.BASE_URL,
                    headers={
                        "x-api-key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": query,
                        "numResults": num_results,
                        "useAutoprompt": use_autoprompt,
                        "type": "neural",  # Semantic search
                        "category": "research paper",  # Focus on research content
                        "startPublishedDate": (
                            datetime.now() - timedelta(days=settings.news_lookback_days)
                        ).isoformat(),
                    },
                )
                search_response.raise_for_status()
                search_data = search_response.json()
                
                results = search_data.get("results", [])
                if not results:
                    logger.info(f"No Exa results found for '{query}'")
                    return []
                
                # Step 2: Get full content for the URLs
                ids = [r["id"] for r in results]
                contents_response = await client.post(
                    self.CONTENTS_URL,
                    headers={
                        "x-api-key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "ids": ids,
                        "text": {
                            "maxCharacters": 5000,  # Get substantial content
                            "includeHtmlTags": False,
                        },
                    },
                )
                contents_response.raise_for_status()
                contents_data = contents_response.json()
                
                # Step 3: Combine search results with content
                articles = []
                contents_map = {c["id"]: c for c in contents_data.get("results", [])}
                
                for result in results:
                    result_id = result["id"]
                    content_data = contents_map.get(result_id, {})
                    
                    # Parse published date
                    pub_date = result.get("publishedDate")
                    if pub_date:
                        try:
                            pub_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                        except:
                            pub_date = None
                    
                    articles.append(
                        {
                            "title": result.get("title", "Untitled"),
                            "url": result.get("url", ""),
                            "published_date": pub_date,
                            "description": content_data.get("text", "")[:500],  # Summary
                            "content": content_data.get("text", ""),  # Full content
                            "author": result.get("author"),
                            "source_type": "exa",
                            "metadata": {
                                "score": result.get("score", 0),
                                "autoprompt_string": search_data.get("autopromptString"),
                                "domain": result.get("url", "").split("/")[2] if result.get("url") else None,
                            },
                        }
                    )
                
                logger.info(f"Fetched {len(articles)} articles from Exa for '{query}'")
                return articles
                
        except httpx.HTTPStatusError as exc:
            logger.error(f"Exa API HTTP error for '{query}': {exc.response.status_code} - {exc.response.text}")
            return []
        except Exception as exc:
            logger.warning(f"Exa search failed for '{query}': {exc}")
            return []
