"""
Screening of deduplicated papers against explicit inclusion/exclusion rules.

WHY every paper gets a recorded decision (not just the survivors):
the reproducibility principle requires exclusion criteria to be visible and
auditable. A researcher reviewing RIOS's output should be able to see not
just which papers were used, but *why* others were screened out — this is
standard systematic-review practice (think PRISMA flow diagrams).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rios.core.logging_setup import get_logger
from rios.core.schemas import Paper, ScreeningDecision

logger = get_logger(__name__)


@dataclass
class ScreeningCriteria:
    """Explicit, human-adjustable screening rules. Defaults are deliberately
    conservative (won't silently discard borderline papers) — tighten them
    per-project via the UI or config, not by editing this file."""

    require_abstract: bool = True
    min_citation_count: int = 0
    must_include_keywords: list[str] = field(default_factory=list)  # ANY match required
    must_exclude_keywords: list[str] = field(default_factory=list)  # ANY match excludes


def _text_blob(paper: Paper) -> str:
    return " ".join(
        filter(None, [paper.title, paper.abstract or "", " ".join(paper.keywords)])
    ).lower()


def screen_papers(
    papers: list[Paper], criteria: ScreeningCriteria
) -> tuple[list[Paper], list[Paper], list[ScreeningDecision]]:
    """Apply criteria to every paper.

    Returns (included_papers, excluded_papers, all_decisions) — the decisions
    list has exactly one entry per input paper, included or not, so it can be
    persisted as a full audit trail regardless of the outcome.
    """
    included: list[Paper] = []
    excluded: list[Paper] = []
    decisions: list[ScreeningDecision] = []

    for paper in papers:
        reasons: list[str] = []
        blob = _text_blob(paper)

        if criteria.require_abstract and not paper.abstract:
            reasons.append("Missing abstract")

        if (paper.citation_count or 0) < criteria.min_citation_count:
            reasons.append(
                f"Citation count {paper.citation_count or 0} below minimum "
                f"{criteria.min_citation_count}"
            )

        if criteria.must_include_keywords and not any(
            kw.lower() in blob for kw in criteria.must_include_keywords
        ):
            reasons.append(
                f"Does not mention any required keyword: {criteria.must_include_keywords}"
            )

        matched_excludes = [
            kw for kw in criteria.must_exclude_keywords if kw.lower() in blob
        ]
        if matched_excludes:
            reasons.append(f"Matched exclusion keyword(s): {matched_excludes}")

        is_included = len(reasons) == 0
        decisions.append(
            ScreeningDecision(paper_id=paper.id, included=is_included, reasons=reasons)
        )
        (included if is_included else excluded).append(paper)

    logger.info(
        "Screening: %d included, %d excluded (of %d)",
        len(included), len(excluded), len(papers),
    )
    return included, excluded, decisions
