"""
JSON report generation.

WHY this exists alongside the Word report: the .docx is for a human to
read; this is the complete, structured, machine-readable version of the
same record — useful for archiving, re-importing into another tool, or
simply as the most literal form of the reproducibility record your
principles require (every field, with nothing summarized or dropped).
"""

from __future__ import annotations

import json

from rios.core.schemas import (
    JournalRecommendation,
    MethodologyRecommendation,
    Paper,
    ResearchGapCandidate,
    SearchStrategy,
)


def build_gap_report_json(
    gap: ResearchGapCandidate,
    papers_by_id: dict[str, Paper],
    methodology_recs: list[MethodologyRecommendation],
    journal_recs: list[JournalRecommendation],
    strategy: SearchStrategy | None,
) -> str:
    """Return a pretty-printed JSON string containing the full record for
    one gap — nothing summarized, every validated field included."""
    supporting_papers = [
        papers_by_id[pid] for pid in gap.supporting_paper_ids if pid in papers_by_id
    ]
    payload = {
        "gap": json.loads(gap.model_dump_json()),
        "supporting_papers": [json.loads(p.model_dump_json()) for p in supporting_papers],
        "methodology_recommendations": [json.loads(m.model_dump_json()) for m in methodology_recs],
        "journal_recommendations": [json.loads(j.model_dump_json()) for j in journal_recs],
        "search_strategy": json.loads(strategy.model_dump_json()) if strategy else None,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)
