"""Deduplication and screening of retrieved literature."""

from rios.ingestion.dedup import dedup_papers
from rios.ingestion.screening import ScreeningCriteria, screen_papers

__all__ = ["dedup_papers", "ScreeningCriteria", "screen_papers"]

