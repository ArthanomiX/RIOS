from unittest.mock import patch

from rios.core.schemas import Paper, SearchStrategy
from rios.literature.multi_source import search_all_sources


def _paper(source: str, paper_id: str) -> Paper:
    return Paper(id=paper_id, title=f"Paper from {source}", source=source)


@patch("rios.literature.multi_source.search_semantic_scholar")
@patch("rios.literature.multi_source.search_crossref")
@patch("rios.literature.multi_source.search_openalex")
def test_combines_results_from_all_sources(mock_oa, mock_cr, mock_s2):
    mock_oa.return_value = ([_paper("openalex", "W1")], None)
    mock_cr.return_value = ([_paper("crossref", "10.1/x")], None)
    mock_s2.return_value = ([_paper("semantic_scholar", "abc")], None)

    papers, strategy, errors = search_all_sources(
        keywords=["test"], year_min=2020, year_max=2026,
        sources=["OpenAlex", "Crossref", "Semantic Scholar"],
    )
    assert len(papers) == 3
    assert set(strategy.databases_searched) == {"OpenAlex", "Crossref", "Semantic Scholar"}
    assert errors == {}


@patch("rios.literature.multi_source.search_semantic_scholar")
@patch("rios.literature.multi_source.search_crossref")
@patch("rios.literature.multi_source.search_openalex")
def test_one_source_failing_does_not_lose_others(mock_oa, mock_cr, mock_s2):
    mock_oa.return_value = ([_paper("openalex", "W1")], None)
    mock_cr.side_effect = RuntimeError("Crossref down")
    mock_s2.return_value = ([_paper("semantic_scholar", "abc")], None)

    papers, strategy, errors = search_all_sources(
        keywords=["test"], year_min=2020, year_max=2026,
        sources=["OpenAlex", "Crossref", "Semantic Scholar"],
    )
    assert len(papers) == 2  # OpenAlex + Semantic Scholar results still present
    assert "Crossref" in errors
    assert "Crossref" not in strategy.databases_searched


@patch("rios.literature.multi_source.search_openalex")
def test_only_selected_sources_are_queried(mock_oa):
    mock_oa.return_value = ([_paper("openalex", "W1")], None)
    papers, strategy, errors = search_all_sources(
        keywords=["test"], year_min=2020, year_max=2026, sources=["OpenAlex"],
    )
    assert strategy.databases_searched == ["OpenAlex"]
    mock_oa.assert_called_once()
