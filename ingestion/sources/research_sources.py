"""
Academic research source integrations.
"""
from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from config import get_settings

settings = get_settings()


class ArxivFetcher:
    """Fetch papers from the arXiv API."""

    BASE_URL = "https://export.arxiv.org/api/query"
    ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
    ARXIV_NS = {"arxiv": "http://arxiv.org/schemas/atom"}

    async def search(
        self,
        keywords: List[str],
        max_results: int = 50,
        categories: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        if categories is None:
            categories = ["cs.AI", "cs.CL", "cs.LG", "cs.IR"]

        papers: List[Dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for i, keyword in enumerate(keywords[:5]):
                try:
                    category_query = " OR ".join(f"cat:{category}" for category in categories)
                    search_query = f'all:"{keyword}" AND ({category_query})'
                    
                    # Retry with exponential backoff for rate limits
                    for attempt in range(3):
                        try:
                            response = await client.get(
                                self.BASE_URL,
                                params={
                                    "search_query": search_query,
                                    "sortBy": "submittedDate",
                                    "sortOrder": "descending",
                                    "max_results": max_results,
                                },
                            )
                            response.raise_for_status()
                            papers.extend(self._parse_entries(response.text))
                            break  # Success, exit retry loop
                        except httpx.HTTPStatusError as http_exc:
                            if http_exc.response.status_code == 429:
                                wait_time = (2 ** attempt) * 3  # 3s, 6s, 12s
                                if attempt < 2:
                                    logger.warning(f"arXiv rate limit hit for '{keyword}', waiting {wait_time}s (attempt {attempt + 1}/3)")
                                    await asyncio.sleep(wait_time)
                                else:
                                    logger.error(f"arXiv rate limit persists for '{keyword}' after 3 attempts, skipping")
                                    raise
                            else:
                                raise
                    
                    # Always wait 3 seconds between successful requests
                    if i < len(keywords[:5]) - 1:  # Don't wait after last keyword
                        await asyncio.sleep(3)
                        
                except Exception as exc:
                    logger.warning(f"arXiv query failed for '{keyword}': {exc}")

        deduped = self._dedupe_by_url(papers)
        logger.info(f"Fetched {len(deduped)} unique papers from arXiv")
        return deduped[:max_results]

    def _parse_entries(self, payload: str) -> List[Dict[str, Any]]:
        root = ET.fromstring(payload)
        results: List[Dict[str, Any]] = []

        for entry in root.findall("atom:entry", self.ATOM_NS):
            try:
                published_text = self._node_text(entry, "atom:published")
                published = datetime.fromisoformat(published_text.replace("Z", "+00:00"))
                if published.year < settings.min_publication_year:
                    continue

                entry_id = self._node_text(entry, "atom:id")
                pdf_url = None
                for link in entry.findall("atom:link", self.ATOM_NS):
                    if link.get("title") == "pdf":
                        pdf_url = link.get("href")
                        break

                doi_node = entry.find("arxiv:doi", self.ARXIV_NS)
                results.append(
                    {
                        "title": self._node_text(entry, "atom:title").strip(),
                        "abstract": self._node_text(entry, "atom:summary").strip(),
                        "authors": [
                            author.find("atom:name", self.ATOM_NS).text.strip()
                            for author in entry.findall("atom:author", self.ATOM_NS)
                            if author.find("atom:name", self.ATOM_NS) is not None
                        ],
                        "publication_date": published.date().isoformat(),
                        "url": pdf_url or entry_id,
                        "source_type": "arxiv",
                        "metadata": {
                            "arxiv_id": entry_id.rsplit("/", 1)[-1],
                            "pdf_url": pdf_url,
                            "categories": [
                                category.get("term")
                                for category in entry.findall("atom:category", self.ATOM_NS)
                                if category.get("term")
                            ],
                            "doi": doi_node.text.strip() if doi_node is not None and doi_node.text else None,
                        },
                    }
                )
            except Exception as exc:
                logger.debug(f"Skipping malformed arXiv entry: {exc}")

        return results

    @staticmethod
    def _node_text(entry: ET.Element, path: str) -> str:
        node = entry.find(path, ArxivFetcher.ATOM_NS)
        return node.text if node is not None and node.text else ""

    @staticmethod
    def _dedupe_by_url(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen: set[str] = set()
        deduped: List[Dict[str, Any]] = []
        for paper in papers:
            url = paper.get("url") or ""
            if not url or url in seen:
                continue
            seen.add(url)
            deduped.append(paper)
        return deduped


class SemanticScholarFetcher:
    """Fetch papers from Semantic Scholar."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self) -> None:
        self.api_key = settings.semantic_scholar_api_key
        self.headers = {"x-api-key": self.api_key} if self.api_key else {}

    async def search(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        if fields is None:
            fields = [
                "title",
                "abstract",
                "authors",
                "year",
                "citationCount",
                "influentialCitationCount",
                "tldr",
                "openAccessPdf",
                "url",
                "publicationDate",
                "fieldsOfStudy",
                "paperId",
            ]

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    f"{self.BASE_URL}/paper/search",
                    params={
                        "query": query,
                        "fields": ",".join(fields),
                        "limit": limit,
                        "year": f"{settings.min_publication_year}-",
                    },
                    headers=self.headers,
                )
                response.raise_for_status()
        except Exception as exc:
            logger.warning(f"Semantic Scholar fetch failed for '{query}': {exc}")
            return []

        payload = response.json()
        papers: List[Dict[str, Any]] = []
        for paper in payload.get("data", []):
            papers.append(
                {
                    "title": paper.get("title", ""),
                    "abstract": paper.get("abstract") or paper.get("tldr", {}).get("text", ""),
                    "authors": [author.get("name", "") for author in paper.get("authors", []) if author.get("name")],
                    "publication_date": paper.get("publicationDate") or str(paper.get("year", "")),
                    "url": paper.get("url", ""),
                    "source_type": "semantic_scholar",
                    "metadata": {
                        "paper_id": paper.get("paperId", ""),
                        "citation_count": paper.get("citationCount", 0),
                        "influential_citation_count": paper.get("influentialCitationCount", 0),
                        "fields_of_study": paper.get("fieldsOfStudy", []),
                        "pdf_url": (paper.get("openAccessPdf") or {}).get("url"),
                    },
                }
            )

        logger.info(f"Fetched {len(papers)} papers from Semantic Scholar for '{query}'")
        return papers


class OpenAlexFetcher:
    """Fetch papers from OpenAlex."""

    BASE_URL = "https://api.openalex.org/works"

    def __init__(self) -> None:
        self.headers = {
            "User-Agent": f"ResearchAgent/1.0 (mailto:{settings.openalex_contact_email})"
        }

    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        if filters is None:
            filters = {
                "publication_year": f">{settings.min_publication_year - 1}",
                "is_oa": "true",
            }

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "search": query,
                        "filter": ",".join(f"{key}:{value}" for key, value in filters.items()),
                        "per_page": limit,
                        "sort": "publication_date:desc",
                    },
                    headers=self.headers,
                )
                response.raise_for_status()
        except Exception as exc:
            logger.warning(f"OpenAlex fetch failed for '{query}': {exc}")
            return []

        payload = response.json()
        papers: List[Dict[str, Any]] = []
        for work in payload.get("results", []):
            papers.append(
                {
                    "title": work.get("title", ""),
                    "abstract": self._reconstruct_abstract(work.get("abstract_inverted_index")),
                    "authors": [
                        authorship.get("author", {}).get("display_name", "")
                        for authorship in work.get("authorships", [])
                        if authorship.get("author", {}).get("display_name")
                    ],
                    "publication_date": work.get("publication_date", ""),
                    "url": work.get("doi") or work.get("id", ""),
                    "source_type": "openalex",
                    "metadata": {
                        "openalex_id": work.get("id", ""),
                        "citation_count": work.get("cited_by_count", 0),
                        "concepts": [
                            concept.get("display_name", "")
                            for concept in work.get("concepts", [])[:5]
                            if concept.get("display_name")
                        ],
                        "doi": work.get("doi"),
                        "pdf_url": (
                            work.get("primary_location", {}) or {}
                        ).get("pdf_url")
                        or (work.get("best_oa_location", {}) or {}).get("pdf_url"),
                        "is_open_access": (work.get("open_access") or {}).get("is_oa", False),
                    },
                }
            )

        logger.info(f"Fetched {len(papers)} papers from OpenAlex for '{query}'")
        return papers

    @staticmethod
    def _reconstruct_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> str:
        if not inverted_index:
            return ""

        words_with_positions: List[tuple[int, str]] = []
        for word, positions in inverted_index.items():
            for position in positions:
                words_with_positions.append((position, word))

        words_with_positions.sort(key=lambda item: item[0])
        return " ".join(word for _, word in words_with_positions)


class HuggingFacePapersFetcher:
    """Fetch daily papers from Hugging Face Papers."""

    BASE_URL = "https://huggingface.co/api/daily_papers"

    def __init__(self) -> None:
        self.token = settings.huggingface_token
        self.headers = {}
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    async def fetch_daily_papers(
        self,
        date: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetch daily curated papers from Hugging Face."""
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={"date": date},
                    headers=self.headers,
                )
                response.raise_for_status()
        except Exception as exc:
            logger.warning(f"Hugging Face Papers fetch failed for date '{date}': {exc}")
            return []

        payload = response.json()
        papers: List[Dict[str, Any]] = []
        for paper in payload[:limit]:
            papers.append(
                {
                    "title": paper.get("title", ""),
                    "abstract": paper.get("summary", ""),
                    "authors": [author.get("name", "") for author in paper.get("authors", []) if author.get("name")],
                    "publication_date": paper.get("publishedAt", "")[:10],
                    "url": f"https://huggingface.co/papers/{paper.get('paper', {}).get('id', '')}",
                    "source_type": "huggingface_papers",
                    "metadata": {
                        "paper_id": paper.get("paper", {}).get("id", ""),
                        "arxiv_id": paper.get("paper", {}).get("arxivId"),
                        "upvotes": paper.get("upvotes", 0),
                        "num_comments": paper.get("numComments", 0),
                        "hf_url": f"https://huggingface.co/papers/{paper.get('paper', {}).get('id', '')}",
                    },
                }
            )

        logger.info(f"Fetched {len(papers)} papers from Hugging Face Daily Papers")
        return papers

    async def search_datasets(
        self,
        query: str,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """Search Hugging Face datasets."""
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    "https://huggingface.co/api/datasets",
                    params={
                        "search": query,
                        "limit": limit,
                        "sort": "downloads",
                        "direction": -1,
                    },
                    headers=self.headers,
                )
                response.raise_for_status()
        except Exception as exc:
            logger.warning(f"Hugging Face Datasets search failed for '{query}': {exc}")
            return []

        datasets: List[Dict[str, Any]] = []
        for dataset in response.json():
            datasets.append(
                {
                    "title": dataset.get("id", ""),
                    "content": dataset.get("description") or dataset.get("cardData", {}).get("description", ""),
                    "authors": [dataset.get("author", "Unknown")],
                    "publication_date": (dataset.get("createdAt") or "")[:10],
                    "url": f"https://huggingface.co/datasets/{dataset.get('id', '')}",
                    "source_type": "huggingface_datasets",
                    "metadata": {
                        "dataset_id": dataset.get("id", ""),
                        "downloads": dataset.get("downloads", 0),
                        "likes": dataset.get("likes", 0),
                        "tags": dataset.get("tags", []),
                        "task_categories": dataset.get("cardData", {}).get("task_categories", []),
                    },
                }
            )

        logger.info(f"Fetched {len(datasets)} datasets from Hugging Face")
        return datasets


class PapersWithCodeFetcher:
    """Fetch papers and their code implementations from Papers with Code."""

    BASE_URL = "https://paperswithcode.com/api/v1"

    async def search_papers(
        self,
        query: Optional[str] = None,
        items_per_page: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search papers on Papers with Code."""
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                params = {"items_per_page": items_per_page}
                if query:
                    params["q"] = query

                response = await client.get(
                    f"{self.BASE_URL}/papers/",
                    params=params,
                )
                response.raise_for_status()
        except Exception as exc:
            logger.warning(f"Papers with Code fetch failed: {exc}")
            return []

        payload = response.json()
        papers: List[Dict[str, Any]] = []
        for paper in payload.get("results", []):
            papers.append(
                {
                    "title": paper.get("title", ""),
                    "abstract": paper.get("abstract", ""),
                    "authors": [author.get("name", "") for author in paper.get("authors", []) if author.get("name")],
                    "publication_date": paper.get("published", "")[:10] if paper.get("published") else "",
                    "url": paper.get("url_pdf") or paper.get("paper_url", ""),
                    "source_type": "papers_with_code",
                    "metadata": {
                        "paper_id": paper.get("id", ""),
                        "arxiv_id": paper.get("arxiv_id"),
                        "url_abs": paper.get("url_abs"),
                        "url_pdf": paper.get("url_pdf"),
                        "proceeding": paper.get("proceeding"),
                        "conference": paper.get("conference"),
                        "tasks": [task.get("name", "") for task in paper.get("tasks", [])],
                        "methods": [method.get("name", "") for method in paper.get("methods", [])],
                        "pwc_url": f"https://paperswithcode.com{paper.get('paper_url', '')}",
                    },
                }
            )

        logger.info(f"Fetched {len(papers)} papers from Papers with Code")
        return papers

    async def get_trending_papers(
        self,
        since: str = "month",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get trending papers from Papers with Code."""
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    "https://paperswithcode.com/api/v1/papers/",
                    params={
                        "ordering": "-stars_count",
                        "items_per_page": limit,
                    },
                )
                response.raise_for_status()
                return await self._parse_papers_response(response)
        except Exception as exc:
            logger.warning(f"Papers with Code trending fetch failed: {exc}")
            return []

    async def _parse_papers_response(self, response: httpx.Response) -> List[Dict[str, Any]]:
        """Parse Papers with Code API response."""
        payload = response.json()
        papers: List[Dict[str, Any]] = []
        for paper in payload.get("results", []):
            papers.append(
                {
                    "title": paper.get("title", ""),
                    "abstract": paper.get("abstract", ""),
                    "authors": [author.get("name", "") for author in paper.get("authors", []) if author.get("name")],
                    "publication_date": paper.get("published", "")[:10] if paper.get("published") else "",
                    "url": paper.get("url_pdf") or paper.get("paper_url", ""),
                    "source_type": "papers_with_code",
                    "metadata": {
                        "paper_id": paper.get("id", ""),
                        "arxiv_id": paper.get("arxiv_id"),
                        "stars_count": paper.get("stars_count", 0),
                    },
                }
            )
        return papers


class AminerFetcher:
    """Fetch papers from Aminer / AMiner.org."""

    BASE_URL = "https://api.aminer.org/api"

    def __init__(self) -> None:
        self.api_key = settings.aminer_api_key

    async def search_papers(
        self,
        query: str,
        size: int = 50,
        sort: str = "relevance",
    ) -> List[Dict[str, Any]]:
        """Search papers on Aminer."""
        if not self.api_key:
            logger.info("Aminer API key not configured, skipping")
            return []

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    f"{self.BASE_URL}/search/pub",
                    params={
                        "query": query,
                        "size": size,
                        "sort": sort,
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
        except Exception as exc:
            logger.warning(f"Aminer fetch failed for '{query}': {exc}")
            return []

        payload = response.json()
        papers: List[Dict[str, Any]] = []
        for hit in payload.get("result", []):
            paper = hit
            papers.append(
                {
                    "title": paper.get("title", ""),
                    "abstract": paper.get("abstract", ""),
                    "authors": [
                        author.get("name", "") 
                        for author in paper.get("authors", []) 
                        if author.get("name")
                    ],
                    "publication_date": str(paper.get("year", "")),
                    "url": paper.get("url") or paper.get("doi", ""),
                    "source_type": "aminer",
                    "metadata": {
                        "paper_id": paper.get("id", ""),
                        "citation_count": paper.get("n_citation", 0),
                        "venue": paper.get("venue", {}).get("name") if isinstance(paper.get("venue"), dict) else paper.get("venue"),
                        "doi": paper.get("doi"),
                        "pdf_url": paper.get("pdf"),
                        "keywords": paper.get("keywords", []),
                    },
                }
            )

        logger.info(f"Fetched {len(papers)} papers from Aminer for '{query}'")
        return papers
