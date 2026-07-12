"""
Deduplication of retrieved papers.

WHY a two-pass approach (exact DOI match, then fuzzy title match):
- DOI is the most reliable identifier when present — an exact match is
  unambiguous, no fuzziness needed.
- Not every paper has a DOI, and the same paper can appear with slightly
  different titles across sources (trailing punctuation, subtitle
  formatting, preprint vs. published version). A fuzzy title comparison
  catches these without a shared identifier.
- When two records represent the same paper, we keep the one with *more*
  usable metadata (abstract present, higher citation count) rather than
  arbitrarily keeping "whichever came first" — later modules (screening,
  RAG) work better with richer records.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from rios.core.logging_setup import get_logger
from rios.core.schemas import Paper

logger = get_logger(__name__)

TITLE_SIMILARITY_THRESHOLD = 0.92


def _normalize_title(title: str) -> str:
    return " ".join(title.lower().strip().split())


def _is_richer(candidate: Paper, existing: Paper) -> bool:
    """True if `candidate` has more usable metadata than `existing`."""
    candidate_score = (
        (1 if candidate.abstract else 0)
        + (candidate.citation_count or 0) / 1000  # tiny tiebreaker, not dominant
    )
    existing_score = (
        (1 if existing.abstract else 0)
        + (existing.citation_count or 0) / 1000
    )
    return candidate_score > existing_score


def dedup_papers(papers: list[Paper]) -> tuple[list[Paper], int]:
    """Remove duplicate papers. Returns (deduplicated_list, num_removed).

    Pass 1 — exact DOI match.
    Pass 2 — fuzzy title match among papers that survived pass 1.
    """
    # Pass 1: exact DOI dedup
    by_doi: dict[str, Paper] = {}
    no_doi: list[Paper] = []
    for paper in papers:
        if paper.doi:
            key = paper.doi.strip().lower()
            if key not in by_doi or _is_richer(paper, by_doi[key]):
                by_doi[key] = paper
        else:
            no_doi.append(paper)

    stage_one = list(by_doi.values()) + no_doi

    # Pass 2: fuzzy title dedup
    kept: list[Paper] = []
    for paper in stage_one:
        normalized = _normalize_title(paper.title)
        duplicate_index = None
        for i, existing in enumerate(kept):
            similarity = SequenceMatcher(
                None, normalized, _normalize_title(existing.title)
            ).ratio()
            if similarity >= TITLE_SIMILARITY_THRESHOLD:
                duplicate_index = i
                break
        if duplicate_index is None:
            kept.append(paper)
        elif _is_richer(paper, kept[duplicate_index]):
            kept[duplicate_index] = paper

    removed = len(papers) - len(kept)
    logger.info("Dedup: %d -> %d papers (%d removed)", len(papers), len(kept), removed)
    return kept, removed
