"""
Unit tests for rios.core.config.

Run with: pytest

WHY test config first: if settings.yaml or domains.yaml drift out of sync
with the Pydantic models (e.g. someone renames a YAML key), every downstream
module breaks silently at import time. Catching that here, in a fast test,
is much cheaper than discovering it mid-pipeline.
"""

from rios.core.config import get_settings


def test_settings_load_without_error():
    settings = get_settings()
    assert settings.app.name
    assert settings.app.version


def test_domains_are_loaded():
    settings = get_settings()
    assert isinstance(settings.domains, list)
    assert len(settings.domains) > 0
    assert "Agricultural Economics" in settings.domains


def test_literature_defaults_have_sane_year_range():
    settings = get_settings()
    d = settings.literature_defaults
    assert d.publication_year_min < d.publication_year_max
