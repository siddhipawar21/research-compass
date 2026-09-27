"""SQLite evidence store and SerpApi response normalization."""

from __future__ import annotations

import json
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

from pydantic import BaseModel, Field

YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


class EvidenceItem(BaseModel):
    id: str
    run_id: str
    engine: str
    source_type: str
    quality: str
    title: str
    snippet: str = ""
    url: str = ""
    year: int | None = None
    authors: list[str] = Field(default_factory=list)
    venue: str = ""
    cited_by: int | None = None
    query: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)

    def short_label(self) -> str:
        year = f" ({self.year})" if self.year else ""
        return f"{self.id}: {self.title[:80]}{year}"


def infer_source_type(engine: str, url: str, title: str = "") -> str:
    host = urlparse(url or "").netloc.lower()
    blob = f"{host} {title}".lower()
    if engine == "google_scholar":
        return "paper"
    if engine == "google_news":
        return "news"
    if engine == "google_trends":
        return "trends"
    if engine == "google_scholar_profiles":
        return "author"
    if engine == "google_scholar_author":
        return "author"
    if "github.com" in host:
        return "github"
    if any(x in blob for x in ("huggingface.co", "kaggle.com", "zenodo.org", "figshare", "dataverse")):
        return "dataset"
    if "paperswithcode.com" in host:
        return "reimplementation"
    if any(x in blob for x in ("grant", "fellowship", "cfp", "call for papers", "workshop", "conference")):
        return "venue"
    if engine == "google":
        return "web"
    return "other"


def infer_quality(source_type: str, url: str, extra: Mapping[str, Any] | None = None) -> str:
    extra = extra or {}
    host = urlparse(url or "").netloc.lower()
    if source_type == "paper":
        return "peer_reviewed"
    if source_type == "news":
        return "news"
    if source_type in {"github", "dataset", "reimplementation"}:
        return "repo"
    if extra.get("cited_by"):
        return "peer_reviewed"
    if any(x in host for x in ("arxiv.org", "acm.org", "ieee.org", "springer", "nature.com", "sciencedirect")):
        return "peer_reviewed"
    if any(x in host for x in ("medium.com", "substack", "blogspot", "wordpress", "dev.to")):
        return "blog"
    if source_type == "web":
        return "web"
    return "other"


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        names: list[str] = []
        for item in value:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict):
                name = item.get("name") or item.get("author") or item.get("title")
                if name:
                    names.append(str(name))
        return names
    if isinstance(value, str):
        return [p.strip() for p in value.split(",") if p.strip()]
    return []


def _year_from(*candidates: Any) -> int | None:
    for c in candidates:
        if c is None:
            continue
        if isinstance(c, int) and 1900 <= c <= 2100:
            return c
        text = str(c)
        m = YEAR_RE.search(text)
        if m:
            y = int(m.group(0))
            if 1900 <= y <= 2100:
                return y
    return None


def _text(*vals: Any) -> str:
    for v in vals:
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, dict):
            for k in ("name", "title", "snippet", "summary"):
                if v.get(k):
                    return str(v[k]).strip()
    return ""


def flatten_news_results(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in payload.get("news_results") or []:
        if not isinstance(item, dict):
            continue
        rows.append(item)
        stories = item.get("stories") or item.get("highlight")
        if isinstance(stories, list):
            for s in stories:
                if isinstance(s, dict):
                    rows.append(s)
    return rows


def extract_items(engine: str, payload: Mapping[str, Any], query: str) -> list[dict[str, Any]]:
    """Defensively flatten a SerpApi payload into raw item dicts."""
    raw: list[dict[str, Any]] = []
    if not isinstance(payload, Mapping):
        return raw

    if engine == "google_scholar":
        for item in payload.get("organic_results") or []:
            if isinstance(item, dict):
                raw.append(item)
    elif engine == "google":
        for key in ("organic_results", "top_stories", "news_results", "answer_box"):
            block = payload.get(key)
            if isinstance(block, dict):
                raw.append(block)
            elif isinstance(block, list):
                raw.extend(x for x in block if isinstance(x, dict))
    elif engine == "google_news":
        raw.extend(flatten_news_results(payload))
    elif engine == "google_trends":
        iot = payload.get("interest_over_time") or {}
        timeline = iot.get("timeline_data") or []
        averages = iot.get("averages") or []
        raw.append(
            {
                "title": f"Google Trends: {query}",
                "link": "",
                "snippet": json.dumps({"averages": averages, "points": len(timeline)})[:500],
                "timeline_data": timeline,
                "averages": averages,
            }
        )
        related = (payload.get("related_queries") or {}).get("rising") or []
        for rq in related[:8]:
            if isinstance(rq, dict):
                raw.append(
                    {
                        "title": f"Related rising query: {rq.get('query', '')}",
                        "link": "",
                        "snippet": str(rq),
                    }
                )
    elif engine == "google_scholar_profiles":
        for p in payload.get("profiles") or []:
            if isinstance(p, dict):
                raw.append(p)
    elif engine == "google_scholar_author":
        author = payload.get("author") or {}
        if isinstance(author, dict) and author:
            raw.append(author)
        for art in payload.get("articles") or []:
            if isinstance(art, dict):
                raw.append(art)
    else:
        for key in ("organic_results", "news_results", "profiles", "articles"):
            block = payload.get(key)
            if isinstance(block, list):
                raw.extend(x for x in block if isinstance(x, dict))
    return raw


def normalize_item(
    engine: str,
    item: Mapping[str, Any],
    *,
    query: str,
    run_id: str,
    seq: int,
) -> EvidenceItem:
    url = _text(item.get("link"), item.get("url"), (item.get("resources") or [{}])[0].get("link") if item.get("resources") else "")
    from core.citations import is_valid_source_url

    if is_valid_source_url(url):
        url = url.strip()
        link_status = "verified"
    elif (url or "").strip():
        url = ""
        link_status = "invalid"
    else:
        url = ""
        link_status = "unavailable"
    title = _text(item.get("title"), item.get("name"), item.get("query"), "Untitled result")
    snippet = _text(
        item.get("snippet"),
        item.get("snippet_highlighted_words")[0] if isinstance(item.get("snippet_highlighted_words"), list) and item.get("snippet_highlighted_words") else "",
        (item.get("publication_info") or {}).get("summary") if isinstance(item.get("publication_info"), dict) else "",
        item.get("affiliations"),
        item.get("publication"),
        item.get("description"),
    )
    pub = item.get("publication_info") if isinstance(item.get("publication_info"), dict) else {}
    authors = _as_list(item.get("authors") or pub.get("authors") or item.get("author"))
    cited = None
    inline = item.get("inline_links") if isinstance(item.get("inline_links"), dict) else {}
    cited_block = inline.get("cited_by") if isinstance(inline.get("cited_by"), dict) else item.get("cited_by")
    if isinstance(cited_block, dict):
        cited = cited_block.get("total") or cited_block.get("value")
    elif isinstance(cited_block, int):
        cited = cited_block
    try:
        cited = int(cited) if cited is not None else None
    except (TypeError, ValueError):
        cited = None

    year = _year_from(item.get("year"), item.get("date"), pub.get("summary"), snippet, title)
    source_type = infer_source_type(engine, url, title)
    extra = {
        k: item.get(k)
        for k in (
            "result_id",
            "author_id",
            "cited_by",
            "interests",
            "timeline_data",
            "averages",
            "type",
            "source",
        )
        if k in item
    }
    if item.get("author_id"):
        extra["scholar_user"] = item.get("author_id")
    extra["link_status"] = link_status
    quality = infer_quality(source_type, url, {"cited_by": cited})
    venue = _text(item.get("publication"), pub.get("summary"))
    source_name = item.get("source")
    if isinstance(source_name, dict):
        venue = venue or _text(source_name.get("name"))
    elif isinstance(source_name, str):
        venue = venue or source_name

    return EvidenceItem(
        id=f"SRC-{seq:03d}",
        run_id=run_id,
        engine=engine,
        source_type=source_type,
        quality=quality,
        title=title[:300],
        snippet=snippet[:800],
        url=url,
        year=year,
        authors=authors[:12],
        venue=venue[:240],
        cited_by=cited,
        query=query,
        extra=extra,
    )


class EvidenceStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else Path(":memory:")
        self._memory = str(self.path) == ":memory:" or path is None
        self.run_id = uuid.uuid4().hex[:12]
        self._items: list[EvidenceItem] = []
        self._seen_keys: set[str] = set()
        self._conn = sqlite3.connect(":memory:" if self._memory else self.path)
        self._conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                run_id TEXT,
                engine TEXT,
                source_type TEXT,
                quality TEXT,
                title TEXT,
                snippet TEXT,
                url TEXT,
                year INTEGER,
                authors_json TEXT,
                venue TEXT,
                cited_by INTEGER,
                query TEXT,
                extra_json TEXT,
                created_at REAL
            )
            """
        )
        self._conn.commit()

    def new_run(self) -> str:
        self.run_id = uuid.uuid4().hex[:12]
        self._items = []
        self._seen_keys = set()
        self._conn.execute("DELETE FROM evidence")
        self._conn.commit()
        return self.run_id

    def ingest_search(self, engine: str, payload: Mapping[str, Any], query: str) -> list[EvidenceItem]:
        created: list[EvidenceItem] = []
        for raw in extract_items(engine, payload, query):
            seq = len(self._items) + 1
            item = normalize_item(engine, raw, query=query, run_id=self.run_id, seq=seq)
            # Drop near-empty rows.
            if not item.title or item.title == "Untitled result":
                if not item.url and not item.snippet:
                    continue
            key = (item.url or "").rstrip("/").lower() or item.title.strip().lower()
            if key and key in self._seen_keys:
                continue
            if key:
                self._seen_keys.add(key)
            self._insert(item)
            created.append(item)
        return created

    def add(self, item: EvidenceItem) -> None:
        self._insert(item)

    def _insert(self, item: EvidenceItem) -> None:
        self._items.append(item)
        self._conn.execute(
            """
            INSERT OR REPLACE INTO evidence VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.id,
                item.run_id,
                item.engine,
                item.source_type,
                item.quality,
                item.title,
                item.snippet,
                item.url,
                item.year,
                json.dumps(item.authors),
                item.venue,
                item.cited_by,
                item.query,
                json.dumps(item.extra),
                time.time(),
            ),
        )
        self._conn.commit()

    def all(self) -> list[EvidenceItem]:
        return list(self._items)

    def by_id(self, source_id: str) -> EvidenceItem | None:
        for item in self._items:
            if item.id == source_id:
                return item
        return None

    def ids(self) -> set[str]:
        return {i.id for i in self._items}

    def filter(self, *, engine: str | None = None, source_type: str | None = None) -> list[EvidenceItem]:
        rows = self._items
        if engine:
            rows = [r for r in rows if r.engine == engine]
        if source_type:
            rows = [r for r in rows if r.source_type == source_type]
        return rows

    def to_llm_context(self, limit: int = 80) -> str:
        lines = []
        for item in self._items[:limit]:
            authors = ", ".join(item.authors[:4])
            lines.append(
                f"[{item.id}] type={item.source_type} quality={item.quality} year={item.year} "
                f"cited_by={item.cited_by} engine={item.engine}\n"
                f"  title: {item.title}\n"
                f"  authors: {authors}\n"
                f"  url: {item.url}\n"
                f"  snippet: {item.snippet[:280]}\n"
            )
        return "\n".join(lines) if lines else "(no evidence items)"

    def publication_years(self) -> dict[int, int]:
        counts: dict[int, int] = {}
        for item in self._items:
            if item.source_type == "paper" and item.year:
                counts[item.year] = counts.get(item.year, 0) + 1
        return dict(sorted(counts.items()))


def validate_source_ids(cited: Iterable[str], store: EvidenceStore) -> tuple[list[str], list[str]]:
    known = store.ids()
    valid, invalid = [], []
    for sid in cited:
        if not sid:
            continue
        if sid in known:
            valid.append(sid)
        else:
            invalid.append(sid)
    return valid, invalid
