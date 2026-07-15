from rios.core.schemas import Paper, ResearchGapCandidate
from rios.journals.recommender import recommend_journals


def _paper(**overrides) -> Paper:
    defaults = dict(id="W1", title="Title", source="test")
    defaults.update(overrides)
    return Paper(**defaults)


def _gap(supporting_ids: list[str]) -> ResearchGapCandidate:
    return ResearchGapCandidate(
        gap_id="g1", domain="Ag Econ", gap_type="empirical",
        description="d", why_insufficient="w", expected_contribution="e",
        supporting_paper_ids=supporting_ids, confidence_score=0.7,
        prompt_version="v1", model_version="gemini-2.5-flash",
    )


def test_recommends_journal_from_supporting_papers():
    papers = {
        "W1": _paper(id="W1", journal="Journal of Ag Econ", citation_count=10),
        "W2": _paper(id="W2", journal="Journal of Ag Econ", citation_count=5),
        "W3": _paper(id="W3", journal="Food Policy", citation_count=2),
    }
    gap = _gap(["W1", "W2", "W3"])
    recs = recommend_journals(gap, papers)
    assert recs[0].journal_name == "Journal of Ag Econ"  # 2 papers > 1
    assert recs[0].paper_count == 2
    assert recs[0].total_citations == 15


def test_papers_without_journal_are_skipped():
    papers = {"W1": _paper(id="W1", journal=None)}
    gap = _gap(["W1"])
    assert recommend_journals(gap, papers) == []


def test_only_supporting_papers_considered():
    papers = {
        "W1": _paper(id="W1", journal="Journal A"),
        "W99": _paper(id="W99", journal="Journal B"),  # not in gap's support
    }
    gap = _gap(["W1"])
    recs = recommend_journals(gap, papers)
    assert len(recs) == 1
    assert recs[0].journal_name == "Journal A"


def test_reason_mentions_verification_caveat():
    papers = {"W1": _paper(id="W1", journal="Journal A")}
    gap = _gap(["W1"])
    recs = recommend_journals(gap, papers)
    assert "verify" in recs[0].reason_for_recommendation.lower()
