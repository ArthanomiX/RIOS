"""
OpenAlex literature retrieval client.

WHY this file's shape:
- One pure function, `search_openalex`, takes plain arguments and returns
  `list[Paper]`. No class, no hidden state — easy to test, easy to call from
  Streamlit or from a later orchestration module without setup.
- Every OpenAlex result is validated into the shared `Paper` schema at the
  boundary. If OpenAlex changes a field name or type, this raises immediately
  here — not silently three modules downstream in gap generation.
- Network calls are wrapped with retries + timeout. Academic APIs occasionally
  hiccup; one flaky request should not crash an entire literature search.
- `mailto` is passed on every request because OpenAlex gives faster, more
  reliable rate limits to requests that identify a contact email (their
  "polite pool"). We already collect this in .env (OPENALEX_MAILTO).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import requests

from rios.core.logging_setup import get_logger
from rios.core.schemas import Paper, SearchStrategy

logger = get_logger(__name__)

OPENALEX_BASE_URL = "https://api.openalex.org/works"
DEFAULT_TIMEOUT_SECONDS = 15
MAX_RETRIES = 3


def _build_filter_string(year_min: int, year_max: int) -> str:
    """OpenAlex uses a comma-separated `filter` query param, not multiple
    query params, for combined conditions."""
    return f"from_publication_date:{year_min}-01-01,to_publication_date:{year_max}-12-31"


def _reconstruct_abstract(inverted_index: dict | None) -> str | None:
    """OpenAlex stores abstracts as an 'inverted index' (word -> positions)
    instead of plain text, for copyright reasons. We rebuild the plain text
    from it so downstream modules (RAG, extraction) can work with it normally.
    """
    if not inverted_index:
        return None
    position_to_word: dict[int, str] = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            position_to_word[pos] = word
    if not position_to_word:
        return None
    ordered = [position_to_word[i] for i in sorted(position_to_word.keys())]
    return " ".join(ordered)


def _to_paper(raw: dict) -> Paper | None:
    """Convert one raw OpenAlex 'work' record into a validated Paper.
    Returns None (and logs) if the record is missing a usable title/id —
    better to skip a bad record than crash the whole search.
    """
    try:
        authors = [
            a.get("author", {}).get("display_name", "")
            for a in raw.get("authorships", [])
            if a.get("author", {}).get("display_name")
        ]
        primary_location = raw.get("primary_location") or {}
        source = primary_location.get("source") or {}

        return Paper(
            id=raw["id"],
            title=raw.get("title") or "Untitled",
            authors=authors,
            year=raw.get("publication_year"),
            journal=source.get("display_name"),
            doi=raw.get("doi"),
            abstract=_reconstruct_abstract(raw.get("abstract_inverted_index")),
            keywords=[c.get("display_name", "") for c in raw.get("concepts", [])[:8]],
            citation_count=raw.get("cited_by_count"),
            open_access=(raw.get("open_access") or {}).get("is_oa"),
            source="openalex",
            url=raw.get("id"),
        )
    except (KeyError, TypeError) as exc:
        logger.warning("Skipping malformed OpenAlex record: %s", exc)
        return None


def search_openalex(
    keywords: list[str],
    year_min: int,
    year_max: int,
    max_results: int = 50,
    mailto: str = "",
) -> tuple[list[Paper], SearchStrategy]:
    """Search OpenAlex and return (papers, search_strategy).

    Returning the SearchStrategy alongside the papers — rather than just the
    papers — is what makes this reproducible: every downstream report can
    show exactly how this list of papers was produced.
    """
    query = " ".join(keywords)
    params = {
        "search": query,
        "filter": _build_filter_string(year_min, year_max),
        "per-page": min(max_results, 200),  # OpenAlex hard cap per page
    }
    if mailto:
        params["mailto"] = mailto

    papers: list[Paper] = []
    last_exception: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                OPENALEX_BASE_URL, params=params, timeout=DEFAULT_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            data = response.json()
            for raw_work in data.get("results", []):
                paper = _to_paper(raw_work)
                if paper is not None:
                    papers.append(paper)
            logger.info(
                "OpenAlex search succeeded: query=%r results=%d", query, len(papers)
            )
            break
        except (requests.RequestException, ValueError) as exc:
            last_exception = exc
            logger.warning("OpenAlex request attempt %d/%d failed: %s",
                            attempt, MAX_RETRIES, exc)
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)  # exponential backoff: 2s, 4s
    else:
        # All retries exhausted — surface a clear error rather than
        # returning an empty list that looks like "no papers found".
        raise RuntimeError(
            f"OpenAlex search failed after {MAX_RETRIES} attempts"
        ) from last_exception

    strategy = SearchStrategy(
        domain=query,
        keywords=keywords,
        databases_searched=["OpenAlex"],
        publication_year_min=year_min,
        publication_year_max=year_max,
        journal_quartiles_allowed=[],  # OpenAlex has no quartile field; filtered later
        inclusion_criteria=[f"Published between {year_min} and {year_max}"],
        exclusion_criteria=[],
        executed_at=datetime.now(timezone.utc),
    )
    return papers, strategy
