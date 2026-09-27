"""SerpApi client with SQLite cache, credit budget, retries, and defensive errors."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

import requests

from core.config import ALLOWED_ENGINES, ENGINE_ALIASES

Fetcher = Callable[[str, dict[str, Any], int], dict[str, Any]]


def normalize_engine(engine: str) -> str:
    key = (engine or "").strip().lower()
    mapped = ENGINE_ALIASES.get(key, key)
    if mapped not in ALLOWED_ENGINES:
        raise ValueError(f"Unsupported SerpApi engine: {engine!r}")
    return mapped


def normalize_params(params: Mapping[str, Any]) -> dict[str, str]:
    """Stable, comparable param dict (excludes api_key)."""
    skip = {"api_key", "output", "no_cache", "async"}
    out: dict[str, str] = {}
    for k, v in params.items():
        if k in skip or v is None:
            continue
        s = str(v).strip()
        if s == "":
            continue
        out[k] = s
    return dict(sorted(out.items()))


def cache_key(engine: str, params: Mapping[str, Any]) -> str:
    payload = json.dumps({"engine": engine, "params": normalize_params(params)}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class SearchCapExceeded(Exception):
    """Raised internally when the per-run paid-search cap is hit; caller should not crash."""


@dataclass
class SearchOutcome:
    engine: str
    params: dict[str, str]
    data: dict[str, Any]
    cached: bool
    error: str | None = None
    skipped: bool = False


@dataclass
class CreditMeter:
    used_this_run: int = 0
    cache_hits_this_run: int = 0
    skipped_this_run: int = 0
    errors_this_run: int = 0
    messages: list[str] = field(default_factory=list)

    def note(self, msg: str) -> None:
        self.messages.append(msg)


class SearchCache:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS search_cache (
                    cache_key TEXT PRIMARY KEY,
                    engine TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    from_network INTEGER NOT NULL
                )
                """
            )
            conn.commit()

    def get(self, key: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT response_json FROM search_cache WHERE cache_key = ?",
                (key,),
            ).fetchone()
        if not row:
            return None
        return json.loads(row["response_json"])

    def put(
        self,
        key: str,
        engine: str,
        params: Mapping[str, Any],
        data: Mapping[str, Any],
        *,
        from_network: bool,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO search_cache
                (cache_key, engine, params_json, response_json, created_at, from_network)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    engine,
                    json.dumps(normalize_params(params), sort_keys=True),
                    json.dumps(data),
                    time.time(),
                    1 if from_network else 0,
                ),
            )
            conn.commit()

    def total_entries(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM search_cache").fetchone()
        return int(row["n"] if row else 0)

    def preload_fixture(self, engine: str, params: Mapping[str, Any], data: Mapping[str, Any]) -> None:
        engine = normalize_engine(engine)
        key = cache_key(engine, params)
        self.put(key, engine, params, data, from_network=False)


def default_fetcher(url: str, params: dict[str, Any], timeout: int) -> dict[str, Any]:
    resp = requests.get(url, params=params, timeout=timeout)
    if resp.status_code == 429:
        raise requests.HTTPError("429 rate limited", response=resp)
    if resp.status_code >= 500:
        raise requests.HTTPError(f"{resp.status_code} server error", response=resp)
    try:
        payload = resp.json()
    except json.JSONDecodeError as exc:
        raise ValueError(f"SerpApi returned non-JSON (HTTP {resp.status_code})") from exc
    if resp.status_code >= 400:
        err = payload.get("error") if isinstance(payload, dict) else None
        raise requests.HTTPError(err or f"HTTP {resp.status_code}", response=resp)
    return payload


class SerpClient:
    """Cached SerpApi wrapper. Never crashes the app on a failed search."""

    def __init__(
        self,
        api_key: str,
        cache_path: str | Path,
        *,
        max_searches: int = 20,
        timeout: int = 45,
        endpoint: str = "https://serpapi.com/search.json",
        fetcher: Fetcher | None = None,
        max_retries: int = 3,
    ):
        self.api_key = api_key
        self.cache = SearchCache(cache_path)
        self.max_searches = max_searches
        self.timeout = timeout
        self.endpoint = endpoint
        self.fetcher = fetcher or default_fetcher
        self.max_retries = max_retries
        self.meter = CreditMeter()

    def reset_run(self) -> None:
        self.meter = CreditMeter()

    def search(self, engine: str, **params: Any) -> SearchOutcome:
        try:
            engine = normalize_engine(engine)
        except ValueError as exc:
            self.meter.errors_this_run += 1
            self.meter.note(str(exc))
            return SearchOutcome(engine=engine, params={}, data={}, cached=False, error=str(exc))

        clean = normalize_params(params)
        key = cache_key(engine, clean)
        hit = self.cache.get(key)
        if hit is not None:
            self.meter.cache_hits_this_run += 1
            return SearchOutcome(engine=engine, params=clean, data=hit, cached=True)

        if self.meter.used_this_run >= self.max_searches:
            msg = (
                f"Search skipped: per-run credit cap of {self.max_searches} reached "
                f"(cached {self.meter.cache_hits_this_run} hits this run)."
            )
            self.meter.skipped_this_run += 1
            self.meter.note(msg)
            return SearchOutcome(
                engine=engine, params=clean, data={}, cached=False, error=msg, skipped=True
            )

        if not self.api_key:
            msg = "Research search is currently unavailable. Please configure the required API credentials."
            self.meter.errors_this_run += 1
            self.meter.note(msg)
            return SearchOutcome(engine=engine, params=clean, data={}, cached=False, error=msg)

        request_params = {"engine": engine, "api_key": self.api_key, **clean}
        data, err = self._fetch_with_retry(request_params)
        if err:
            self.meter.errors_this_run += 1
            self.meter.note(f"{engine}: {err}")
            return SearchOutcome(engine=engine, params=clean, data={}, cached=False, error=err)

        self.meter.used_this_run += 1
        self.cache.put(key, engine, clean, data, from_network=True)
        return SearchOutcome(engine=engine, params=clean, data=data, cached=False)

    def _fetch_with_retry(self, params: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
        last_err = "unknown error"
        for attempt in range(self.max_retries):
            try:
                payload = self.fetcher(self.endpoint, params, self.timeout)
                if not isinstance(payload, dict):
                    return {}, "SerpApi returned an unexpected payload shape."
                api_err = payload.get("error")
                if api_err:
                    # Do not cache API-level errors; they may be transient or quota.
                    return {}, str(api_err)
                return payload, None
            except requests.Timeout:
                last_err = "SerpApi request timed out."
            except requests.HTTPError as exc:
                status = getattr(exc.response, "status_code", None)
                if status == 429:
                    last_err = "SerpApi rate limit (HTTP 429)."
                    time.sleep(1.5 * (2**attempt))
                    continue
                last_err = str(exc)
            except requests.RequestException as exc:
                last_err = f"Network error talking to SerpApi: {exc}"
            except Exception as exc:  # noqa: BLE001 — never crash the report run
                last_err = f"SerpApi client error: {exc}"
            time.sleep(0.4 * (2**attempt))
        return {}, last_err
