"""
Core data contracts shared across every RIOS module.

WHY this exists as its own file, first, before any retrieval/RAG/gap logic:
every later module (literature retrieval, screening, gap generation, human
review, report writing) passes data to the next module. If each module
invents its own shape for "a paper" or "a research gap," integration between
modules becomes a constant translation problem. Defining the shared schema
once means every module speaks the same language from day one.

These are Pydantic models rather than plain dicts because:
1. Validation — a paper missing a required field fails immediately, not deep
   inside a report generator.
2. Self-documentation — the fields ARE the spec for what "a paper" means.
3. Easy JSON serialization for logging / review history / audit trail.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class Paper(BaseModel):
    """A single piece of retrieved scholarly literature (metadata only)."""

    id: str                      # e.g. OpenAlex ID or DOI — used for dedup
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    journal: str | None = None
    doi: str | None = None
    abstract: str | None = None
    keywords: list[str] = Field(default_factory=list)
    citation_count: int | None = None
    open_access: bool | None = None
    source: str = ""            # "openalex" | "crossref" | "semantic_scholar" ...
    url: str | None = None


class SearchStrategy(BaseModel):
    """Records exactly how a literature search was run — required for
    reproducibility (STEP in the reproducibility principle: search strategy,
    databases, keywords, inclusion/exclusion criteria, etc.)."""

    domain: str
    keywords: list[str]
    databases_searched: list[str]
    publication_year_min: int
    publication_year_max: int
    journal_quartiles_allowed: list[str]
    inclusion_criteria: list[str] = Field(default_factory=list)
    exclusion_criteria: list[str] = Field(default_factory=list)
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReviewStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    MODIFIED = "modified"
    REJECTED = "rejected"


class ResearchGapCandidate(BaseModel):
    """A candidate research gap proposed by the system.

    Per the evidence-before-generation principle, this must NEVER be
    constructed from model memory alone — `supporting_paper_ids` must be
    non-empty and traceable back to a Paper.id that was actually retrieved.
    """

    gap_id: str
    domain: str
    gap_type: str                 # methodological | empirical | theoretical | ...
    description: str
    why_insufficient: str         # why existing literature falls short
    expected_contribution: str
    supporting_paper_ids: list[str]
    confidence_score: float = Field(ge=0.0, le=1.0)
    prompt_version: str
    model_version: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Human-in-the-loop fields
    review_status: ReviewStatus = ReviewStatus.PENDING
    review_comment: str | None = None
    reviewed_at: datetime | None = None


class ReviewDecision(BaseModel):
    """One entry in the permanent review history log — never overwritten,
    only appended to, so the full decision trail is reproducible."""

    target_id: str                # e.g. a gap_id
    decision: ReviewStatus
    comment: str | None = None
    reviewer: str = "Suman_Econ (UAS-B)"
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
