from rios.core.schemas import Paper
from rios.ingestion.dedup import dedup_papers


def _paper(**overrides) -> Paper:
    defaults = dict(
        id="W1", title="Price Volatility in Agricultural Markets", year=2022,
        doi="10.1000/example", abstract=None, citation_count=0, source="test",
    )
    defaults.update(overrides)
    return Paper(**defaults)


def test_exact_doi_duplicates_are_merged():
    a = _paper(id="W1", doi="10.1000/example", abstract=None)
    b = _paper(id="W2", doi="10.1000/EXAMPLE", abstract="Has an abstract")  # same DOI, diff case
    result, removed = dedup_papers([a, b])
    assert len(result) == 1
    assert removed == 1
    assert result[0].abstract == "Has an abstract"  # richer record kept


def test_fuzzy_title_duplicates_are_merged():
    a = _paper(id="W1", doi=None, title="Price Volatility in Agricultural Markets")
    b = _paper(id="W2", doi=None, title="Price Volatility in Agricultural Markets.")
    result, removed = dedup_papers([a, b])
    assert len(result) == 1
    assert removed == 1


def test_distinct_papers_are_not_merged():
    a = _paper(id="W1", doi="10.1/a", title="Price Volatility in Agricultural Markets")
    b = _paper(id="W2", doi="10.1/b", title="Climate Change Impacts on Coffee Yields")
    result, removed = dedup_papers([a, b])
    assert len(result) == 2
    assert removed == 0


def test_richer_record_wins_on_title_dedup():
    a = _paper(id="W1", doi=None, title="Same Title Here", abstract=None, citation_count=2)
    b = _paper(id="W2", doi=None, title="Same Title Here", abstract="rich abstract", citation_count=50)
    result, _ = dedup_papers([a, b])
    assert result[0].id == "W2"
