"""
Crossref literature retrieval client.

WHY this mirrors openalex.py's shape closely: `search_crossref` returns the
same (list[Paper], SearchStrategy) contract as `search_openalex`, so the
multi-source combiner (multi_source.py) and everything downstream can treat
every source identically — the rest of the pipeline never needs to know or
care which database a Paper came from.

Crossref quirks handled here:
- Abstracts, when present, are wrapped in JATS XML tags (e.g. <jats:p>) —
  stripped to plain text.
- Author names come as {given, family} objects, not a single display name.
- No API key needed; a `mailto` parameter is still honored, since Crossref
  documents it as a "polite pool" signal for more reliable service.
"""

from __future__ import annotations

import re
import time

import requests

from rios.core.logging_setup import get_logger
from rios.core.schemas import Paper, SearchStrategy

logger = get_logger(__name__)

CROSSREF_BASE_URL = "https://api.crossref.org/works"
DEFAULT_TIMEOUT_SECONDS = 15
MAX_RETRIES = 3

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(text: str | None) -> str | None:
    if not text:
        return None
    return _TAG_RE.sub("", text).strip() or None


def _author_display_name(author: dict) -> str:
    given = author.get("given", "")
    family = author.get("family", "")
    return " ".join(part for part in (given, family) if part).strip()


def _extract_year(item: dict) -> int | None:
    date_parts = (item.get("issued") or {}).get("date-parts") or []
    if date_parts and date_parts[0]:
        return date_parts[0][0]
    return None


def _to_paper(item: dict) -> Paper | None:
    try:
        titles = item.get("title") or []
        title = titles[0] if titles else None
        if not title or not item.get("DOI"):
            return None  # not enough to identify or dedup this record

        container_titles = item.get("container-title") or []
        authors = [
            _author_display_name(a) for a in item.get("author", []) if _author_display_name(a)
        ]

        return Paper(
            id=item["DOI"],
            title=title,
            authors=authors,
            year=_extract_year(item),
            journal=container_titles[0] if container_titles else None,
            doi=item["DOI"],
            abstract=_strip_tags(item.get("abstract")),
            keywords=item.get("subject", [])[:8],
            citation_count=item.get("is-referenced-by-count"),
            open_access=None,  # Crossref doesn't reliably report this
            source="crossref",
            url=item.get("URL"),
        )
    except (KeyError, TypeError, IndexError) as exc:
        logger.warning("Skipping malformed Crossref record: %s", exc)
        return None


def search_crossref(
    keywords: list[str],
    year_min: int,
    year_max: int,
    max_results: int = 50,
    mailto: str = "",
) -> tuple[list[Paper], SearchStrategy]:
    """Search Crossref and return (papers, search_strategy). Same contract
    as search_openalex — see that module's docstring for why."""
    query = " ".join(keywords)
    params = {
        "query": query,
        "filter": f"from-pub-date:{year_min}-01-01,until-pub-date:{year_max}-12-31",
        "rows": min(max_results, 100),  # Crossref hard cap per page
    }
    if mailto:
        params["mailto"] = mailto

    papers: list[Paper] = []
    last_exception: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                CROSSREF_BASE_URL, params=params, timeout=DEFAULT_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            data = response.json()
            for item in (data.get("message") or {}).get("items", []):
                paper = _to_paper(item)
                if paper is not None:
                    papers.append(paper)
            logger.info(
                "Crossref search succeeded: query=%r results=%d", query, len(papers)
            )
            break
        except (requests.RequestException, ValueError) as exc:
            last_exception = exc
            logger.warning(
                "Crossref request attempt %d/%d failed: %s", attempt, MAX_RETRIES, exc
            )
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
    else:
        raise RuntimeError(f"Crossref search failed after {MAX_RETRIES} attempts") from last_exception

    strategy = SearchStrategy(
        domain=query,
        keywords=keywords,
        databases_searched=["Crossref"],
        publication_year_min=year_min,
        publication_year_max=year_max,
        journal_quartiles_allowed=[],
        inclusion_criteria=[f"Published between {year_min} and {year_max}"],
        exclusion_criteria=[],
    )
    return papers, strategy
