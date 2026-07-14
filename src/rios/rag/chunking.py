"""
Chunking: splits each Paper's text (currently: title + abstract, since we
only retrieve metadata, not full text) into small retrievable Chunks.

WHY chunk at all, if abstracts are already short: consistency. Once a later
module adds full-text retrieval (e.g. from open-access PDFs), the same
chunking function needs to handle both a 150-word abstract and a 6000-word
full text without special-casing. Splitting by sentence groups with a max
character budget handles both cases the same way.

Every chunk keeps `paper_id` so retrieval results are always traceable back
to a specific Paper — required for the evidence-before-generation principle.
"""

from __future__ import annotations

import re

from rios.core.schemas import Chunk, Paper

MAX_CHUNK_CHARS = 600  # generous for an abstract; splits longer text sensibly

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def chunk_paper(paper: Paper) -> list[Chunk]:
    """Return one or more Chunks for a single paper. Title is always
    prepended to the first chunk's text so short queries matching the title
    still retrieve the right paper."""
    source_text = paper.abstract or ""
    if not source_text:
        # No abstract — still index the title alone so the paper is
        # findable, rather than silently dropping it from retrieval.
        return [Chunk(chunk_id=f"{paper.id}::0", paper_id=paper.id, text=paper.title)]

    sentences = _split_sentences(source_text)
    chunks: list[Chunk] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        if current_len + len(sentence) > MAX_CHUNK_CHARS and current:
            chunks.append(" ".join(current))
            current, current_len = [], 0
        current.append(sentence)
        current_len += len(sentence)
    if current:
        chunks.append(" ".join(current))

    return [
        Chunk(
            chunk_id=f"{paper.id}::{i}",
            paper_id=paper.id,
            text=(f"{paper.title}. {text}" if i == 0 else text),
        )
        for i, text in enumerate(chunks)
    ]


def chunk_papers(papers: list[Paper]) -> list[Chunk]:
    """Chunk a whole list of papers into a flat list of Chunks."""
    chunks: list[Chunk] = []
    for paper in papers:
        chunks.extend(chunk_paper(paper))
    return chunks
