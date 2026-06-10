"""
Developer platform source integrations.
"""
from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from config import get_settings

settings = get_settings()


class GitHubFetcher:
    BASE_URL = "https://api.github.com"

    def __init__(self) -> None:
        self.token = settings.github_token
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    async def search_repositories(
        self,
        topics: Optional[List[str]] = None,
        min_stars: int = 100,
        max_results: int = 30,
        include_readme: bool = True,
    ) -> List[Dict[str, Any]]:
        if topics is None:
            topics = settings.github_topics

        repos: List[Dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for topic in topics[:5]:
                try:
                    since_date = (datetime.utcnow() - timedelta(days=365)).strftime("%Y-%m-%d")
                    response = await client.get(
                        f"{self.BASE_URL}/search/repositories",
                        params={
                            "q": f"topic:{topic} stars:>{min_stars} pushed:>{since_date}",
                            "sort": "stars",
                            "order": "desc",
                            "per_page": max_results,
                        },
                        headers=self.headers,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    for repo in payload.get("items", []):
                        readme = await self._fetch_readme(client, repo["full_name"]) if include_readme else ""
                        repos.append(
                            {
                                "title": repo["full_name"],
                                "content": "\n\n".join(
                                    part for part in [repo.get("description", ""), readme] if part
                                ),
                                "authors": [repo.get("owner", {}).get("login", "Unknown")],
                                "publication_date": (repo.get("created_at") or "")[:10],
                                "url": repo.get("html_url", ""),
                                "source_type": "github",
                                "metadata": {
                                    "stars": repo.get("stargazers_count", 0),
                                    "forks": repo.get("forks_count", 0),
                                    "language": repo.get("language", ""),
                                    "topics": repo.get("topics", []),
                                    "last_updated": repo.get("updated_at", ""),
                                    "is_archived": repo.get("archived", False),
                                },
                            }
                        )
                    await asyncio.sleep(1)
                except Exception as exc:
                    logger.warning(f"GitHub fetch failed for topic '{topic}': {exc}")

        deduped: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for repo in repos:
            url = repo.get("url") or ""
            if not url or url in seen:
                continue
            seen.add(url)
            deduped.append(repo)

        logger.info(f"Fetched {len(deduped)} unique GitHub repositories")
        return deduped[:max_results]

    async def _fetch_readme(self, client: httpx.AsyncClient, repo_full_name: str) -> str:
        try:
            response = await client.get(f"{self.BASE_URL}/repos/{repo_full_name}/readme", headers=self.headers)
            response.raise_for_status()
            encoded = response.json().get("content", "")
            if not encoded:
                return ""
            return base64.b64decode(encoded).decode("utf-8", errors="ignore")[:5000]
        except Exception:
            return ""


class HackerNewsFetcher:
    BASE_URL = "https://hn.algolia.com/api/v1/search"

    async def search(
        self,
        keywords: Optional[List[str]] = None,
        days_back: int = 30,
        min_points: int = 10,
    ) -> List[Dict[str, Any]]:
        if keywords is None:
            keywords = settings.news_keywords[:5]

        stories: List[Dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for keyword in keywords:
                try:
                    since_timestamp = int((datetime.utcnow() - timedelta(days=days_back)).timestamp())
                    response = await client.get(
                        self.BASE_URL,
                        params={
                            "query": keyword,
                            "tags": "story",
                            "numericFilters": f"created_at_i>{since_timestamp},points>{min_points}",
                            "hitsPerPage": 50,
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                    for hit in payload.get("hits", []):
                        stories.append(
                            {
                                "title": hit.get("title", ""),
                                "content": hit.get("story_text") or hit.get("title", ""),
                                "authors": [hit.get("author", "Unknown")],
                                "publication_date": datetime.utcfromtimestamp(hit["created_at_i"]).date().isoformat(),
                                "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}",
                                "source_type": "hackernews",
                                "metadata": {
                                    "points": hit.get("points", 0),
                                    "num_comments": hit.get("num_comments", 0),
                                    "hn_url": f"https://news.ycombinator.com/item?id={hit['objectID']}",
                                },
                            }
                        )
                    await asyncio.sleep(0.5)
                except Exception as exc:
                    logger.warning(f"Hacker News fetch failed for '{keyword}': {exc}")

        deduped: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for story in stories:
            url = story.get("url") or ""
            if not url or url in seen:
                continue
            seen.add(url)
            deduped.append(story)

        logger.info(f"Fetched {len(deduped)} unique Hacker News stories")
        return deduped


class GitHubAwesomeListsFetcher:
    """Fetch and parse curated awesome lists from GitHub."""

    BASE_URL = "https://api.github.com"

    def __init__(self) -> None:
        self.token = settings.github_token
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    async def fetch_awesome_lists(
        self,
        repo_list: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch README content from curated awesome lists.
        
        Args:
            repo_list: List of repo names in format "owner/repo" (e.g., "Wrenbjor/awesome-llm")
        """
        if repo_list is None:
            repo_list = settings.github_awesome_lists

        all_entries: List[Dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for repo_full_name in repo_list:
                try:
                    # Fetch repository metadata
                    repo_response = await client.get(
                        f"{self.BASE_URL}/repos/{repo_full_name}",
                        headers=self.headers,
                    )
                    repo_response.raise_for_status()
                    repo_data = repo_response.json()

                    # Fetch README content
                    readme_content = await self._fetch_readme(client, repo_full_name)
                    
                    # Parse links from README (basic extraction)
                    parsed_links = self._parse_readme_links(readme_content)

                    all_entries.append(
                        {
                            "title": f"Awesome List: {repo_data.get('name', '')}",
                            "content": "\n\n".join([
                                repo_data.get("description", ""),
                                f"Stars: {repo_data.get('stargazers_count', 0)}",
                                f"Last Updated: {repo_data.get('updated_at', '')}",
                                f"Links extracted: {len(parsed_links)}",
                                readme_content[:2000],  # Include preview of README
                            ]),
                            "authors": [repo_data.get("owner", {}).get("login", "Unknown")],
                            "publication_date": (repo_data.get("created_at") or "")[:10],
                            "url": repo_data.get("html_url", ""),
                            "source_type": "github_awesome_list",
                            "metadata": {
                                "repo_full_name": repo_full_name,
                                "stars": repo_data.get("stargazers_count", 0),
                                "forks": repo_data.get("forks_count", 0),
                                "topics": repo_data.get("topics", []),
                                "last_updated": repo_data.get("updated_at", ""),
                                "parsed_links": parsed_links[:100],  # Store first 100 links
                                "total_links": len(parsed_links),
                            },
                        }
                    )
                    await asyncio.sleep(1)  # Rate limiting
                except Exception as exc:
                    logger.warning(f"Failed to fetch awesome list '{repo_full_name}': {exc}")

        logger.info(f"Fetched {len(all_entries)} awesome lists from GitHub")
        return all_entries

    async def _fetch_readme(self, client: httpx.AsyncClient, repo_full_name: str) -> str:
        """Fetch README content from a repository."""
        try:
            response = await client.get(
                f"{self.BASE_URL}/repos/{repo_full_name}/readme",
                headers=self.headers,
            )
            response.raise_for_status()
            encoded = response.json().get("content", "")
            if not encoded:
                return ""
            return base64.b64decode(encoded).decode("utf-8", errors="ignore")
        except Exception as exc:
            logger.debug(f"Failed to fetch README for {repo_full_name}: {exc}")
            return ""

    @staticmethod
    def _parse_readme_links(readme_content: str) -> List[Dict[str, str]]:
        """
        Parse markdown links from README content.
        Returns list of dicts with 'text' and 'url' keys.
        """
        import re
        
        # Match markdown links: [text](url)
        link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        matches = re.findall(link_pattern, readme_content)
        
        links = []
        for text, url in matches:
            # Filter out internal links and images
            if url.startswith(('http://', 'https://')) and not url.endswith(('.png', '.jpg', '.gif', '.svg')):
                links.append({
                    "text": text.strip(),
                    "url": url.strip(),
                })
        
        return links
