"""Environment-backed configuration. No secrets are hardcoded."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    serpapi_api_key: str
    anthropic_api_key: str
    anthropic_model: str
    max_searches_per_run: int
    cache_path: Path
    serpapi_timeout: int
    llm_max_retries: int
    serpapi_endpoint: str = "https://serpapi.com/search.json"

    @property
    def has_serpapi(self) -> bool:
        return bool(self.serpapi_api_key)

    @property
    def has_llm(self) -> bool:
        return bool(self.anthropic_api_key)


def load_settings() -> Settings:
    cache = Path(os.getenv("CACHE_PATH", "data/cache.sqlite"))
    if not cache.is_absolute():
        cache = ROOT / cache
    return Settings(
        serpapi_api_key=os.getenv("SERPAPI_API_KEY", "").strip(),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929").strip(),
        max_searches_per_run=_int("MAX_SEARCHES_PER_RUN", 20),
        cache_path=cache,
        serpapi_timeout=_int("SERPAPI_TIMEOUT_SECONDS", 45),
        llm_max_retries=_int("LLM_MAX_RETRIES", 2),
    )


ALLOWED_ENGINES = frozenset(
    {
        "google_scholar",
        "google",
        "google_news",
        "google_trends",
        "google_scholar_profiles",
        "google_scholar_author",
    }
)

# Planner may emit these; mapped to SerpApi engines.
ENGINE_ALIASES = {
    "scholar": "google_scholar",
    "google_scholar": "google_scholar",
    "web": "google",
    "google": "google",
    "news": "google_news",
    "google_news": "google_news",
    "trends": "google_trends",
    "google_trends": "google_trends",
    "scholar_profiles": "google_scholar_profiles",
    "google_scholar_profiles": "google_scholar_profiles",
    "scholar_author": "google_scholar_author",
    "google_scholar_author": "google_scholar_author",
}
