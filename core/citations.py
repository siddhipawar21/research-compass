"""Safe citation URLs: never invent links or attach a URL to the wrong source."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from core.store import EvidenceItem

UNAVAILABLE = "Source link unavailable"

_GENERIC_HOMEPAGES = {
    "https://trends.google.com",
    "https://trends.google.com/",
    "http://trends.google.com",
    "http://trends.google.com/",
}

_SRC_IN_ARXIV = re.compile(r"arxiv\.org/(abs|pdf)/SRC-\d+", re.I)
_SRC_IN_DOI = re.compile(r"doi\.org/.*SRC-\d+", re.I)


def is_http_url(url: str | None) -> bool:
    if not url or not isinstance(url, str):
        return False
    u = url.strip()
    if not u.lower().startswith(("http://", "https://")):
        return False
    if u.lower().startswith(("javascript:", "data:", "vbscript:")):
        return False
    parsed = urlparse(u)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.netloc:
        return False
    return True


_PLACEHOLDER_MARKERS = (
    "example",
    "placeholder",
    "fake",
    "dummy",
    "localhost",
    "demo.research-compass.local",
)


def is_valid_source_url(url: str | None) -> bool:
    """True only for a syntactically real http(s) URL that is not a known placeholder.

    Does not invent a replacement and does not contact the network.
    """
    if not is_http_url(url):
        return False
    u = url.strip()
    if u.rstrip("/").lower() in {x.rstrip("/").lower() for x in _GENERIC_HOMEPAGES}:
        return False
    if _SRC_IN_ARXIV.search(u) or _SRC_IN_DOI.search(u):
        return False
    low = u.lower()
    if any(marker in low for marker in _PLACEHOLDER_MARKERS):
        return False
    return True


def safe_url(url: str | None) -> str | None:
    """Return the original URL when it is valid. Never rewrites or invents one."""
    if is_valid_source_url(url):
        return url.strip()
    return None


def get_verified_source_url(source: EvidenceItem | None) -> str | None:
    """Return the URL stored on this source, or None. Never constructs a replacement."""
    if source is None:
        return None
    raw = source.url
    if not raw:
        return None
    if raw.strip() == source.id or raw.strip().upper() == source.id.upper():
        return None
    if source.id and source.id.upper() in raw.upper() and "arxiv.org" in raw.lower():
        # SRC-001 is not an arXiv identifier.
        if re.search(r"SRC-\d+", raw, re.I):
            return None
    return safe_url(raw)


def url_for_item(item: EvidenceItem | None) -> str | None:
    return get_verified_source_url(item)


def url_for_source(store, source_id: str, claimed_url: str | None = None) -> str | None:
    """Clickable URL is only the store record's URL. claimed_url is ignored (never substituted)."""
    del claimed_url  # do not use secondary/guessed URLs
    if store is None or not source_id:
        return None
    return get_verified_source_url(store.by_id(source_id))


def unique_ids(items: list[EvidenceItem]) -> bool:
    ids = [i.id for i in items]
    return len(ids) == len(set(ids))


def url_title_pairs_are_consistent(items: list[EvidenceItem]) -> bool:
    """The same verified URL cannot be attached to two different titles."""
    by_url: dict[str, str] = {}
    for item in items:
        url = get_verified_source_url(item)
        if not url:
            continue
        key = url.rstrip("/").lower()
        title = (item.title or "").strip().lower()
        if key in by_url and by_url[key] != title:
            return False
        by_url[key] = title
    return True
