from unittest.mock import MagicMock, patch

from rios.core.schemas import Paper, SearchStrategy
from rios.literature.crossref import _strip_tags, _to_paper, search_crossref

FAKE_CROSSREF_RESPONSE = {
    "message": {
        "items": [
            {
                "DOI": "10.1000/example",
                "title": ["Trade Policy and Commodity Exports"],
                "author": [{"given": "A.", "family": "Researcher"}],
                "issued": {"date-parts": [[2021, 6]]},
                "container-title": ["Journal of International Trade"],
                "abstract": "<jats:p>This paper examines trade policy.</jats:p>",
                "subject": ["Economics"],
                "is-referenced-by-count": 7,
                "URL": "https://doi.org/10.1000/example",
            },
            {
                # missing DOI -> should be skipped
                "title": ["Broken record"],
            },
        ]
    }
}


def _mock_response(payload: dict):
    mock_response = MagicMock()
    mock_response.json.return_value = payload
    mock_response.raise_for_status.return_value = None
    return mock_response


def test_strip_tags_removes_jats_markup():
    assert _strip_tags("<jats:p>Hello world.</jats:p>") == "Hello world."


def test_strip_tags_handles_none():
    assert _strip_tags(None) is None


def test_to_paper_maps_fields_correctly():
    paper = _to_paper(FAKE_CROSSREF_RESPONSE["message"]["items"][0])
    assert isinstance(paper, Paper)
    assert paper.title == "Trade Policy and Commodity Exports"
    assert paper.authors == ["A. Researcher"]
    assert paper.year == 2021
    assert paper.abstract == "This paper examines trade policy."
    assert paper.source == "crossref"
    assert paper.citation_count == 7


def test_to_paper_skips_record_without_doi():
    assert _to_paper(FAKE_CROSSREF_RESPONSE["message"]["items"][1]) is None


@patch("rios.literature.crossref.requests.get")
def test_search_crossref_returns_papers_and_strategy(mock_get):
    mock_get.return_value = _mock_response(FAKE_CROSSREF_RESPONSE)
    papers, strategy = search_crossref(
        keywords=["trade", "policy"], year_min=2015, year_max=2026
    )
    assert len(papers) == 1
    assert isinstance(strategy, SearchStrategy)
    assert strategy.databases_searched == ["Crossref"]


@patch("rios.literature.crossref.requests.get")
def test_search_crossref_raises_after_exhausting_retries(mock_get):
    import requests

    mock_get.side_effect = requests.ConnectionError("down")
    try:
        search_crossref(keywords=["test"], year_min=2020, year_max=2026)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "failed after" in str(exc)
