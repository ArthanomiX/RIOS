from rios.core.schemas import Paper
from rios.ingestion.screening import ScreeningCriteria, screen_papers


def _paper(**overrides) -> Paper:
    defaults = dict(
        id="W1", title="Commodity Price Forecasting with Machine Learning",
        abstract="This paper forecasts commodity prices using deep learning.",
        citation_count=10, source="test",
    )
    defaults.update(overrides)
    return Paper(**defaults)


def test_paper_included_when_criteria_met():
    criteria = ScreeningCriteria(require_abstract=True, min_citation_count=5)
    included, excluded, decisions = screen_papers([_paper()], criteria)
    assert len(included) == 1
    assert len(excluded) == 0
    assert decisions[0].included is True
    assert decisions[0].reasons == []


def test_paper_excluded_for_missing_abstract_with_reason():
    criteria = ScreeningCriteria(require_abstract=True)
    paper = _paper(abstract=None)
    included, excluded, decisions = screen_papers([paper], criteria)
    assert len(excluded) == 1
    assert "Missing abstract" in decisions[0].reasons


def test_paper_excluded_below_citation_floor():
    criteria = ScreeningCriteria(min_citation_count=100)
    included, excluded, decisions = screen_papers([_paper(citation_count=3)], criteria)
    assert len(excluded) == 1
    assert any("Citation count" in r for r in decisions[0].reasons)


def test_must_include_keyword_enforced():
    criteria = ScreeningCriteria(must_include_keywords=["climate"])
    included, excluded, decisions = screen_papers([_paper()], criteria)
    assert len(excluded) == 1  # "climate" is not in the fixture text


def test_must_exclude_keyword_removes_paper():
    criteria = ScreeningCriteria(must_exclude_keywords=["forecasting"])
    included, excluded, decisions = screen_papers([_paper()], criteria)
    assert len(excluded) == 1
    assert "forecasting" in decisions[0].reasons[0].lower()


def test_every_paper_gets_exactly_one_decision():
    papers = [_paper(id="W1"), _paper(id="W2", abstract=None)]
    criteria = ScreeningCriteria(require_abstract=True)
    _, _, decisions = screen_papers(papers, criteria)
    assert len(decisions) == 2
    assert {d.paper_id for d in decisions} == {"W1", "W2"}
