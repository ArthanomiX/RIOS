"""Literature retrieval clients (OpenAlex, Crossref, Semantic Scholar) and a combiner."""

from rios.literature.crossref import search_crossref
from rios.literature.multi_source import AVAILABLE_SOURCES, search_all_sources
from rios.literature.openalex import search_openalex
from rios.literature.semantic_scholar import search_semantic_scholar

__all__ = [
    "search_openalex",
    "search_crossref",
    "search_semantic_scholar",
    "search_all_sources",
    "AVAILABLE_SOURCES",
]

