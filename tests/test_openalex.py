"""
Unit tests for rios.literature.openalex.

WHY mocked, not live HTTP calls: tests must be fast, deterministic, and
runnable without network access (e.g. in CI, or in restricted sandboxes).
We mock `requests.get` to return a realistic OpenAlex-shaped payload and
verify our parsing/validation logic, not OpenAlex's uptime.
"""

from unittest.mock import MagicMock, patch

from rios.core.schemas import Paper, SearchStrategy
from rios.literature.openalex import _reconstruct_abstract, _to_paper, search_openalex

FAKE_OPENALEX_RESPONSE = {
    "results": [
        {
            "id": "https://openalex.org/W123",
            "title": "Price Volatility in Agricultural Commodity Markets",
            "publication_year": 2022,
            "doi": "https://doi.org/10.1000/example",
            "authorships": [
                {"author": {"display_name": "A. Researcher"}},
                {"author": {"display_name": "B. Scholar"}},
            ],
            "primary_location": {"source": {"display_name": "Journal of Ag Econ"}},
            "abstract_inverted_index": {
                "Prices": [0],
                "are": [1],
                "volatile.": [2],
            },
            "concepts": [{"display_name": "Agricultural economics"}],
            "cited_by_count": 12,
            "open_access": {"is_oa": True},
        },
        {
            # malformed record: missing "id" -> should be skipped, not crash
            "title": "Broken record",
        },
    ]
}


def test_reconstruct_abstract_rebuilds_word_order():
    inverted = {"Hello": [0], "world": [1]}
    assert _reconstruct_abstract(inverted) == "Hello world"


def test_reconstruct_abstract_handles_none():
    assert _reconstruct_abstract(None) is None


def test_to_paper_maps_fields_correctly():
    paper = _to_paper(FAKE_OPENALEX_RESPONSE["results"][0])
    assert isinstance(paper, Paper)
    assert paper.title == "Price Volatility in Agricultural Commodity Markets"
    assert paper.year == 2022
    assert "A. Researcher" in paper.authors
    assert paper.abstract == "Prices are volatile."
    assert paper.source == "openalex"
    assert paper.open_access is True


def test_to_paper_skips_malformed_record():
    assert _to_paper(FAKE_OPENALEX_RESPONSE["results"][1]) is None


@patch("rios.literature.openalex.requests.get")
def test_search_openalex_returns_papers_and_strategy(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = FAKE_OPENALEX_RESPONSE
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    papers, strategy = search_openalex(
        keywords=["agricultural", "commodity", "prices"],
        year_min=2015,
        year_max=2026,
    )

    assert len(papers) == 1  # malformed record was skipped
    assert isinstance(strategy, SearchStrategy)
    assert strategy.databases_searched == ["OpenAlex"]
    assert strategy.publication_year_min == 2015


@patch("rios.literature.openalex.requests.get")
def test_search_openalex_raises_after_exhausting_retries(mock_get):
    import requests

    mock_get.side_effect = requests.ConnectionError("network down")

    try:
        search_openalex(keywords=["test"], year_min=2020, year_max=2026)
        assert False, "expected RuntimeError to be raised"
    except RuntimeError as exc:
        assert "failed after" in str(exc)
