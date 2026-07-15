"""
Methodology recommendation for an accepted research gap.

WHY grounded, not generated: a recommendation here is only made if the
method is actually MENTIONED somewhere in the text of the gap's supporting
papers. This keeps the recommendation traceable — "3 of your supporting
papers use panel data methods" is a checkable fact, not an LLM guess.
"""

from __future__ import annotations

from rios.core.schemas import Chunk, MethodologyRecommendation, ResearchGapCandidate
from rios.methodology.taxonomy import METHODOLOGY_TAXONOMY


def recommend_methodologies(
    gap: ResearchGapCandidate,
    chunks: list[Chunk],
    top_n: int = 3,
) -> list[MethodologyRecommendation]:
    """Recommend methodologies grounded in the gap's supporting evidence.

    `chunks` should be the full evidence pool used for generation (or any
    superset) — this function filters down to only the chunks belonging to
    `gap.supporting_paper_ids` internally.
    """
    relevant_chunks = [c for c in chunks if c.paper_id in set(gap.supporting_paper_ids)]
    if not relevant_chunks:
        return []

    combined_text_by_paper: dict[str, str] = {}
    for c in relevant_chunks:
        combined_text_by_paper[c.paper_id] = (
            combined_text_by_paper.get(c.paper_id, "") + " " + c.text.lower()
        )

    scored: list[tuple[str, int, list[str]]] = []
    for method_name, meta in METHODOLOGY_TAXONOMY.items():
        matching_papers = [
            paper_id
            for paper_id, text in combined_text_by_paper.items()
            if any(kw in text for kw in meta["keywords"])
        ]
        if matching_papers:
            scored.append((method_name, len(matching_papers), matching_papers))

    if not scored:
        return []

    scored.sort(key=lambda t: t[1], reverse=True)
    top_methods = scored[:top_n]
    alternative_names = [name for name, _, _ in scored[top_n:]]

    recommendations: list[MethodologyRecommendation] = []
    for name, count, paper_ids in top_methods:
        meta = METHODOLOGY_TAXONOMY[name]
        recommendations.append(
            MethodologyRecommendation(
                name=name,
                mention_count=count,
                supporting_paper_ids=paper_ids,
                typical_applications=meta["typical_applications"],
                strengths=meta["strengths"],
                limitations=meta["limitations"],
                alternatives_considered=alternative_names,
                reason_for_recommendation=(
                    f"Mentioned in {count} of {len(relevant_chunks)} supporting "
                    f"evidence passage(s) for this gap."
                ),
            )
        )
    return recommendations
