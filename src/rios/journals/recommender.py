"""
Journal recommendation for an accepted research gap.

WHY grounded, not generated: recommended venues are literally the journals
where the gap's supporting papers were published — never a fabricated "this
looks like a good Q1 journal" guess. This is a starting point for the
researcher, not a quartile/impact-factor guarantee (those require a
separate, licensed data source RIOS doesn't have free access to — flagged
explicitly in the UI, not silently assumed).
"""

from __future__ import annotations

from rios.core.schemas import JournalRecommendation, Paper, ResearchGapCandidate


def recommend_journals(
    gap: ResearchGapCandidate,
    papers_by_id: dict[str, Paper],
    top_n: int = 5,
) -> list[JournalRecommendation]:
    """Recommend journals based on where the gap's supporting papers were
    actually published. Papers with no recorded journal are skipped."""
    supporting_papers = [
        papers_by_id[pid] for pid in gap.supporting_paper_ids if pid in papers_by_id
    ]

    by_journal: dict[str, list[Paper]] = {}
    for paper in supporting_papers:
        if not paper.journal:
            continue
        by_journal.setdefault(paper.journal, []).append(paper)

    if not by_journal:
        return []

    ranked = sorted(
        by_journal.items(),
        key=lambda kv: (len(kv[1]), sum(p.citation_count or 0 for p in kv[1])),
        reverse=True,
    )[:top_n]

    recommendations: list[JournalRecommendation] = []
    for journal_name, papers in ranked:
        titles_preview = "; ".join(p.title for p in papers[:2])
        recommendations.append(
            JournalRecommendation(
                journal_name=journal_name,
                paper_count=len(papers),
                total_citations=sum(p.citation_count or 0 for p in papers),
                supporting_paper_ids=[p.id for p in papers],
                reason_for_recommendation=(
                    f"{len(papers)} supporting paper(s) for this gap were "
                    f"published here, e.g. \"{titles_preview}\". Verify current "
                    f"quartile/impact factor independently before submission."
                ),
            )
        )
    return recommendations
