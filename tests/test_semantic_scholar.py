from unittest.mock import MagicMock, patch

from rios.core.schemas import Paper, SearchStrategy
from rios.literature.semantic_scholar import _to_paper, search_semantic_scholar

FAKE_S2_RESPONSE = {
    "data": [
        {
            "paperId": "abc123",
            "title": "Machine Learning for Crop Yield Prediction",
            "abstract": "We predict crop yields using ML.",
            "year": 2022,
            "authors": [{"name": "B. Scholar"}],
            "venue": "Agricultural Systems",
            "citationCount": 15,
            "isOpenAccess": True,
            "externalIds": {"DOI": "10.2000/example"},
            "url": "https://www.semanticscholar.org/paper/abc123",
        },
        {
            # missing title -> should be skipped
            "paperId": "def456",
        },
    ]
}


def _mock_response(payload: dict):
    mock_response = MagicMock()
    mock_response.json.return_value = payload
    mock_response.raise_for_status.return_value = None
    return mock_response


def test_to_paper_maps_fields_correctly():
    paper = _to_paper(FAKE_S2_RESPONSE["data"][0])
    assert isinstance(paper, Paper)
    assert paper.title == "Machine Learning for Crop Yield Prediction"
    assert paper.doi == "10.2000/example"
    assert paper.source == "semantic_scholar"
    assert paper.open_access is True


def test_to_paper_skips_record_without_title():
    assert _to_paper(FAKE_S2_RESPONSE["data"][1]) is None


@patch("rios.literature.semantic_scholar.requests.get")
def test_search_semantic_scholar_returns_papers_and_strategy(mock_get):
    mock_get.return_value = _mock_response(FAKE_S2_RESPONSE)
    papers, strategy = search_semantic_scholar(
        keywords=["crop", "yield"], year_min=2015, year_max=2026
    )
    assert len(papers) == 1
    assert isinstance(strategy, SearchStrategy)
    assert strategy.databases_searched == ["Semantic Scholar"]


@patch("rios.literature.semantic_scholar.requests.get")
def test_search_semantic_scholar_raises_after_exhausting_retries(mock_get):
    import requests

    mock_get.side_effect = requests.ConnectionError("down")
    try:
        search_semantic_scholar(keywords=["test"], year_min=2020, year_max=2026)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "failed after" in str(exc)
