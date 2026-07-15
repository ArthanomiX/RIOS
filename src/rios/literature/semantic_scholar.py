"""
Semantic Scholar literature retrieval client.

WHY this mirrors openalex.py's shape closely: same (list[Paper],
SearchStrategy) contract as the other source clients — the rest of the
pipeline treats every source identically.

No API key required for the public rate-limited tier, which is more than
sufficient for occasional/personal use. A key can be added later (via the
`api_key` parameter) to unlock a higher personal rate limit if needed.
"""

from __future__ import annotations

import time

import requests

from rios.core.logging_setup import get_logger
from rios.core.schemas import Paper, SearchStrategy

logger = get_logger(__name__)

SEMANTIC_SCHOLAR_BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
DEFAULT_TIMEOUT_SECONDS = 15
MAX_RETRIES = 3
FIELDS = "title,abstract,year,authors,venue,citationCount,isOpenAccess,externalIds,url"


def _to_paper(item: dict) -> Paper | None:
    try:
        paper_id = item.get("paperId")
        title = item.get("title")
        if not paper_id or not title:
            return None

        external_ids = item.get("externalIds") or {}
        return Paper(
            id=paper_id,
            title=title,
            authors=[a.get("name", "") for a in item.get("authors", []) if a.get("name")],
            year=item.get("year"),
            journal=item.get("venue") or None,
            doi=external_ids.get("DOI"),
            abstract=item.get("abstract"),
            keywords=[],  # Semantic Scholar's free search doesn't return keywords/fields of study here
            citation_count=item.get("citationCount"),
            open_access=item.get("isOpenAccess"),
            source="semantic_scholar",
            url=item.get("url"),
        )
    except (KeyError, TypeError) as exc:
        logger.warning("Skipping malformed Semantic Scholar record: %s", exc)
        return None


def search_semantic_scholar(
    keywords: list[str],
    year_min: int,
    year_max: int,
    max_results: int = 50,
    api_key: str = "",
) -> tuple[list[Paper], SearchStrategy]:
    """Search Semantic Scholar and return (papers, search_strategy). Same
    contract as search_openalex — see that module's docstring for why."""
    query = " ".join(keywords)
    params = {
        "query": query,
        "year": f"{year_min}-{year_max}",
        "fields": FIELDS,
        "limit": min(max_results, 100),
    }
    headers = {"x-api-key": api_key} if api_key else {}

    papers: list[Paper] = []
    last_exception: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                SEMANTIC_SCHOLAR_BASE_URL,
                params=params,
                headers=headers,
                timeout=DEFAULT_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
            for item in data.get("data", []):
                paper = _to_paper(item)
                if paper is not None:
                    papers.append(paper)
            logger.info(
                "Semantic Scholar search succeeded: query=%r results=%d", query, len(papers)
            )
            break
        except (requests.RequestException, ValueError) as exc:
            last_exception = exc
            logger.warning(
                "Semantic Scholar request attempt %d/%d failed: %s",
                attempt, MAX_RETRIES, exc,
            )
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
    else:
        raise RuntimeError(
            f"Semantic Scholar search failed after {MAX_RETRIES} attempts"
        ) from last_exception

    strategy = SearchStrategy(
        domain=query,
        keywords=keywords,
        databases_searched=["Semantic Scholar"],
        publication_year_min=year_min,
        publication_year_max=year_max,
        journal_quartiles_allowed=[],
        inclusion_criteria=[f"Published between {year_min} and {year_max}"],
        exclusion_criteria=[],
    )
    return papers, strategy
