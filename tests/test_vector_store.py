from rios.core.schemas import Chunk
from rios.rag.vector_store import VectorStore


def _chunk(chunk_id: str, paper_id: str, text: str) -> Chunk:
    return Chunk(chunk_id=chunk_id, paper_id=paper_id, text=text)


def test_query_returns_most_relevant_chunk_first():
    chunks = [
        _chunk("c1", "W1", "Coffee yields decline under climate change in East Africa."),
        _chunk("c2", "W2", "Commodity price volatility affects farmer income stability."),
        _chunk("c3", "W3", "Deep learning models forecast agricultural prices accurately."),
    ]
    store = VectorStore()
    store.build(chunks)

    results = store.query("price forecasting with machine learning", top_k=2)
    assert len(results) > 0
    assert results[0].chunk.paper_id == "W3"  # most relevant to the query


def test_empty_store_returns_no_results():
    store = VectorStore()
    store.build([])
    assert store.query("anything") == []


def test_query_before_build_returns_empty_not_error():
    store = VectorStore()
    assert store.query("anything") == []


def test_results_are_traceable_to_paper_id():
    chunks = [_chunk("c1", "W99", "Panel data econometrics in trade policy.")]
    store = VectorStore()
    store.build(chunks)
    results = store.query("panel data trade", top_k=1)
    assert results[0].chunk.paper_id == "W99"
