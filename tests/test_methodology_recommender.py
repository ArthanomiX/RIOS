from rios.core.schemas import Chunk, ResearchGapCandidate
from rios.methodology.recommender import recommend_methodologies


def _gap(supporting_ids: list[str]) -> ResearchGapCandidate:
    return ResearchGapCandidate(
        gap_id="g1", domain="Ag Econ", gap_type="methodological",
        description="d", why_insufficient="w", expected_contribution="e",
        supporting_paper_ids=supporting_ids, confidence_score=0.7,
        prompt_version="v1", model_version="gemini-2.5-flash",
    )


def test_recommends_methods_actually_mentioned():
    chunks = [
        Chunk(chunk_id="c1", paper_id="W1", text="This study uses panel data fixed effects regression."),
        Chunk(chunk_id="c2", paper_id="W2", text="We apply a machine learning random forest model."),
    ]
    gap = _gap(["W1", "W2"])
    recs = recommend_methodologies(gap, chunks)
    names = [r.name for r in recs]
    assert "Panel Data Analysis" in names
    assert "Machine Learning / Deep Learning" in names


def test_ignores_chunks_not_linked_to_gap():
    chunks = [
        Chunk(chunk_id="c1", paper_id="W1", text="panel data fixed effects"),
        Chunk(chunk_id="c2", paper_id="W99", text="randomized controlled trial"),
    ]
    gap = _gap(["W1"])  # W99 not a supporting paper
    recs = recommend_methodologies(gap, chunks)
    names = [r.name for r in recs]
    assert "Randomized Controlled Trial" not in names


def test_no_matches_returns_empty_list():
    chunks = [Chunk(chunk_id="c1", paper_id="W1", text="A generic sentence with no method terms.")]
    gap = _gap(["W1"])
    assert recommend_methodologies(gap, chunks) == []


def test_recommendation_includes_audit_fields():
    chunks = [Chunk(chunk_id="c1", paper_id="W1", text="panel data fixed effects regression")]
    gap = _gap(["W1"])
    recs = recommend_methodologies(gap, chunks)
    assert recs[0].strengths
    assert recs[0].limitations
    assert recs[0].typical_applications
    assert recs[0].supporting_paper_ids == ["W1"]
