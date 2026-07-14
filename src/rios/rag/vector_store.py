"""
A lightweight retrieval index over Chunks, using TF-IDF + cosine similarity.

WHY TF-IDF instead of a neural embedding model:
- No model download, no torch/transformers dependency — keeps the Streamlit
  Cloud free-tier app fast to cold-start and light on memory, appropriate
  for occasional personal use rather than production-scale search.
- Good enough for retrieval over a few hundred abstracts, which is the scale
  a single literature search produces.
- The public interface (`build`, `query`) is intentionally narrow, so
  swapping in real embeddings later (e.g. via the Claude API once paid
  generation is already in use) only requires rewriting this one file —
  nothing that calls VectorStore needs to change.
"""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from rios.core.logging_setup import get_logger
from rios.core.schemas import Chunk

logger = get_logger(__name__)


@dataclass
class ScoredChunk:
    chunk: Chunk
    score: float


class VectorStore:
    """Holds a fitted TF-IDF index over a set of chunks. Build once per
    literature search, then query as many times as needed."""

    def __init__(self) -> None:
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = None
        self._chunks: list[Chunk] = []

    def build(self, chunks: list[Chunk]) -> None:
        if not chunks:
            logger.warning("VectorStore.build called with 0 chunks")
            self._chunks = []
            self._matrix = None
            return
        self._chunks = chunks
        texts = [c.text for c in chunks]
        self._matrix = self._vectorizer.fit_transform(texts)
        logger.info("VectorStore built: %d chunks indexed", len(chunks))

    def query(self, text: str, top_k: int = 5) -> list[ScoredChunk]:
        if self._matrix is None or not self._chunks:
            return []
        query_vec = self._vectorizer.transform([text])
        scores = cosine_similarity(query_vec, self._matrix)[0]
        ranked_indices = scores.argsort()[::-1][:top_k]
        return [
            ScoredChunk(chunk=self._chunks[i], score=float(scores[i]))
            for i in ranked_indices
            if scores[i] > 0  # drop zero-similarity results, not useful
        ]
