import json

from rios.core.schemas import Paper, ResearchGapCandidate
from rios.reports.json_report import build_gap_report_json


def _gap() -> ResearchGapCandidate:
    return ResearchGapCandidate(
        gap_id="g1", domain="Ag Econ", gap_type="empirical",
        description="desc", why_insufficient="why", expected_contribution="contribution",
        supporting_paper_ids=["W1"], confidence_score=0.6,
        prompt_version="v1", model_version="gemini-2.5-flash",
    )


def test_json_report_is_valid_json_with_expected_keys():
    gap = _gap()
    paper = Paper(id="W1", title="Title", source="test")
    result = build_gap_report_json(gap, {"W1": paper}, [], [], None)
    parsed = json.loads(result)  # must not raise
    assert set(parsed.keys()) == {
        "gap", "supporting_papers", "methodology_recommendations",
        "journal_recommendations", "search_strategy",
    }
    assert parsed["gap"]["gap_id"] == "g1"
    assert parsed["supporting_papers"][0]["id"] == "W1"


def test_json_report_handles_no_strategy():
    gap = _gap()
    result = build_gap_report_json(gap, {}, [], [], None)
    parsed = json.loads(result)
    assert parsed["search_strategy"] is None
