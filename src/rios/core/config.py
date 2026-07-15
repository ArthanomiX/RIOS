"""
Configuration loading for RIOS.

WHY this design:
- Config lives in human-edited YAML (config/settings.yaml, config/domains.yaml)
  because researchers adjusting filters or thresholds shouldn't need to touch
  Python code.
- We load that YAML into typed Pydantic models rather than passing raw dicts
  around. This means a typo (e.g. "publication_year_min: twenty-fifteen")
  fails loudly at startup, not silently three pipeline stages later.
- Secrets (API keys) never live in YAML — they come from environment
  variables / .env / Streamlit secrets, loaded via pydantic-settings, so they
  can never accidentally get committed to git inside a config file.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve paths relative to the repo root regardless of where the app is run from.
REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = REPO_ROOT / "config"


class LiteratureDefaults(BaseModel):
    publication_year_min: int = 2015
    publication_year_max: int = 2026
    journal_quartiles_allowed: list[str] = Field(default_factory=lambda: ["Q1", "Q2"])
    open_access_only: bool = False
    languages: list[str] = Field(default_factory=lambda: ["English"])


class AppInfo(BaseModel):
    name: str
    author: str
    version: str


class PromptSettings(BaseModel):
    active_version: str = "v1"


class LoggingSettings(BaseModel):
    level: str = "INFO"
    log_dir: str = "data/cache/logs"


class Settings(BaseModel):
    app: AppInfo
    literature_defaults: LiteratureDefaults
    prompts: PromptSettings
    logging: LoggingSettings
    domains: list[str] = Field(default_factory=list)


class Secrets(BaseSettings):
    """Loaded from environment variables / .env / Streamlit secrets.

    Never put real values here — this class only declares which secrets
    are expected. Values are injected at runtime from the environment.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    openalex_mailto: str = ""
    crossref_mailto: str = ""


def _load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and validate settings.yaml + domains.yaml once, then cache.

    lru_cache means every module that calls get_settings() shares the same
    validated object instead of re-reading/re-parsing YAML on every call.
    """
    settings_raw = _load_yaml(CONFIG_DIR / "settings.yaml")
    domains_raw = _load_yaml(CONFIG_DIR / "domains.yaml")

    return Settings(
        app=AppInfo(**settings_raw["app"]),
        literature_defaults=LiteratureDefaults(**settings_raw["literature_defaults"]),
        prompts=PromptSettings(**settings_raw["prompts"]),
        logging=LoggingSettings(**settings_raw["logging"]),
        domains=domains_raw.get("domains", []),
    )


@lru_cache(maxsize=1)
def get_secrets() -> Secrets:
    return Secrets()
