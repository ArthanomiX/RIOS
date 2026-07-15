"""
Multi-source literature search: queries any combination of OpenAlex,
Crossref, and Semantic Scholar, and merges the results.

WHY a combiner function rather than calling each client separately from the
UI: two reasons.

1. Resilience — academic APIs occasionally have outages or rate-limit
   hiccups. If Crossref is briefly down, that should not prevent OpenAlex
   and Semantic Scholar results from coming back. Each source is queried
   independently; a failure in one is logged and skipped, not raised.
2. A single combined SearchStrategy — the reproducibility record should
   show ALL databases actually searched and their combined keyword/year
   scope in one place, not three separate strategy objects the UI has to
   stitch together itself.

Deduplication across sources is intentionally NOT done here — that's
rios.ingestion.dedup_papers's job, applied once, after combining, so the
dedup logic stays in exactly one place regardless of how many sources feed
into it.
"""

from __future__ import annotations

from datetime import datetime, timezone

from rios.core.logging_setup import get_logger
from rios.core.schemas import Paper, SearchStrategy
from rios.literature.crossref import search_crossref
from rios.literature.openalex import search_openalex
from rios.literature.semantic_scholar import search_semantic_scholar

logger = get_logger(__name__)

AVAILABLE_SOURCES = ("OpenAlex", "Crossref", "Semantic Scholar")


def search_all_sources(
    keywords: list[str],
    year_min: int,
    year_max: int,
    sources: list[str],
    max_results_per_source: int = 25,
    openalex_mailto: str = "",
    crossref_mailto: str = "",
) -> tuple[list[Paper], SearchStrategy, dict[str, str]]:
    """Query each selected source independently and merge results.

    Returns (all_papers, combined_strategy, source_errors). `source_errors`
    maps source name -> error message for any source that failed, so the UI
    can show "Crossref search failed: timeout" without losing the results
    that DID come back from the other sources.
    """
    all_papers: list[Paper] = []
    databases_searched: list[str] = []
    source_errors: dict[str, str] = {}

    if "OpenAlex" in sources:
        try:
            papers, _ = search_openalex(
                keywords, year_min, year_max, max_results_per_source, mailto=openalex_mailto
            )
            all_papers.extend(papers)
            databases_searched.append("OpenAlex")
        except RuntimeError as exc:
            logger.warning("OpenAlex source failed in multi-source search: %s", exc)
            source_errors["OpenAlex"] = str(exc)

    if "Crossref" in sources:
        try:
            papers, _ = search_crossref(
                keywords, year_min, year_max, max_results_per_source, mailto=crossref_mailto
            )
            all_papers.extend(papers)
            databases_searched.append("Crossref")
        except RuntimeError as exc:
            logger.warning("Crossref source failed in multi-source search: %s", exc)
            source_errors["Crossref"] = str(exc)

    if "Semantic Scholar" in sources:
        try:
            papers, _ = search_semantic_scholar(
                keywords, year_min, year_max, max_results_per_source
            )
            all_papers.extend(papers)
            databases_searched.append("Semantic Scholar")
        except RuntimeError as exc:
            logger.warning("Semantic Scholar source failed in multi-source search: %s", exc)
            source_errors["Semantic Scholar"] = str(exc)

    combined_strategy = SearchStrategy(
        domain=" ".join(keywords),
        keywords=keywords,
        databases_searched=databases_searched,
        publication_year_min=year_min,
        publication_year_max=year_max,
        journal_quartiles_allowed=[],
        inclusion_criteria=[f"Published between {year_min} and {year_max}"],
        exclusion_criteria=[],
        executed_at=datetime.now(timezone.utc),
    )

    logger.info(
        "Multi-source search: %d total raw results from %s (%d source(s) failed)",
        len(all_papers), databases_searched, len(source_errors),
    )
    return all_papers, combined_strategy, source_errors
