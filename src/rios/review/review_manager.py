"""
Human-in-the-loop review of research gap candidates.

WHY a dedicated module rather than handling this inline in the UI: the
review action — accept / modify / reject, with a permanent reasoned record
— is what makes RIOS's outputs trustworthy and reproducible. Keeping it as
a pure function means the same logic could back a future non-Streamlit
interface (CLI, API) without rewriting the decision logic, and it's testable
without a running UI.

This module NEVER decides anything on its own — every call represents one
explicit human action.
"""

from __future__ import annotations

from datetime import datetime, timezone

from rios.core.schemas import ResearchGapCandidate, ReviewDecision, ReviewStatus


def apply_review(
    gap: ResearchGapCandidate,
    decision: ReviewStatus,
    reviewer: str = "Suman_Econ (UAS-B)",
    comment: str | None = None,
    modified_description: str | None = None,
) -> tuple[ResearchGapCandidate, ReviewDecision]:
    """Apply one human review decision to a gap candidate.

    Returns (updated_gap, review_decision_record). The gap is never mutated
    in place — a new object is returned — and the ReviewDecision record is
    meant to be appended to a permanent, append-only history, never
    overwritten or deleted, so the full decision trail stays reproducible.
    """
    if decision == ReviewStatus.PENDING:
        raise ValueError("A review decision cannot itself be PENDING — that's the default state.")

    updated = gap.model_copy(
        update={
            "review_status": decision,
            "review_comment": comment,
            "reviewed_at": datetime.now(timezone.utc),
            "description": modified_description or gap.description,
        }
    )
    record = ReviewDecision(
        target_id=gap.gap_id,
        decision=decision,
        comment=comment,
        reviewer=reviewer,
    )
    return updated, record
