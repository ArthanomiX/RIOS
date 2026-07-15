import pytest

from rios.core.schemas import ResearchGapCandidate, ReviewStatus
from rios.review.review_manager import apply_review


def _gap(**overrides) -> ResearchGapCandidate:
    defaults = dict(
        gap_id="g1", domain="Ag Econ", gap_type="methodological",
        description="Original description", why_insufficient="why",
        expected_contribution="contribution", supporting_paper_ids=["W1"],
        confidence_score=0.7, prompt_version="v1", model_version="claude-sonnet-5",
    )
    defaults.update(overrides)
    return ResearchGapCandidate(**defaults)


def test_accept_updates_status_and_timestamp():
    gap = _gap()
    updated, record = apply_review(gap, ReviewStatus.ACCEPTED, comment="Looks solid")
    assert updated.review_status == ReviewStatus.ACCEPTED
    assert updated.review_comment == "Looks solid"
    assert updated.reviewed_at is not None
    assert record.decision == ReviewStatus.ACCEPTED
    assert record.target_id == "g1"


def test_reject_with_comment_is_recorded():
    gap = _gap()
    updated, record = apply_review(gap, ReviewStatus.REJECTED, comment="Too vague")
    assert updated.review_status == ReviewStatus.REJECTED
    assert record.comment == "Too vague"


def test_modify_overrides_description():
    gap = _gap()
    updated, _ = apply_review(
        gap, ReviewStatus.MODIFIED, modified_description="A sharper framing of the gap."
    )
    assert updated.description == "A sharper framing of the gap."
    assert updated.review_status == ReviewStatus.MODIFIED


def test_original_gap_object_is_not_mutated():
    gap = _gap()
    apply_review(gap, ReviewStatus.ACCEPTED)
    assert gap.review_status == ReviewStatus.PENDING  # original untouched


def test_pending_decision_is_rejected():
    gap = _gap()
    with pytest.raises(ValueError):
        apply_review(gap, ReviewStatus.PENDING)
