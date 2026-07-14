from rios.core.schemas import Paper
from rios.rag.chunking import chunk_paper, chunk_papers


def _paper(**overrides) -> Paper:
    defaults = dict(id="W1", title="Test Paper", source="test")
    defaults.update(overrides)
    return Paper(**defaults)


def test_short_abstract_becomes_single_chunk():
    paper = _paper(abstract="This is a short abstract about prices.")
    chunks = chunk_paper(paper)
    assert len(chunks) == 1
    assert chunks[0].paper_id == "W1"
    assert "Test Paper" in chunks[0].text  # title prepended


def test_missing_abstract_falls_back_to_title():
    paper = _paper(abstract=None)
    chunks = chunk_paper(paper)
    assert len(chunks) == 1
    assert chunks[0].text == "Test Paper"


def test_long_abstract_splits_into_multiple_chunks():
    sentence = "Commodity prices fluctuate due to weather and demand shocks. "
    long_abstract = sentence * 20  # well over MAX_CHUNK_CHARS
    paper = _paper(abstract=long_abstract)
    chunks = chunk_paper(paper)
    assert len(chunks) > 1
    assert all(c.paper_id == "W1" for c in chunks)


def test_chunk_ids_are_unique_across_papers():
    papers = [_paper(id="W1"), _paper(id="W2")]
    chunks = chunk_papers(papers)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
