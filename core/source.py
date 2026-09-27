"""Canonical source records. Every surface reads URLs from here."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from core.citations import is_valid_source_url
from core.store import EvidenceItem

LINK_VERIFIED = "verified"
LINK_UNAVAILABLE = "unavailable"
LINK_INVALID = "invalid"


class Source(BaseModel):
    source_id: str
    title: str
    url: str | None = None
    source_type: str = "other"
    authors: list[str] = Field(default_factory=list)
    venue: str = ""
    year: int | None = None
    snippet: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    link_status: str = LINK_UNAVAILABLE


def source_from_evidence(item: EvidenceItem) -> Source:
    """Project one evidence row into a Source. Does not look up or invent a URL."""
    raw = (item.url or "").strip()
    if not raw:
        url, status = None, LINK_UNAVAILABLE
    elif is_valid_source_url(raw):
        url, status = raw, LINK_VERIFIED
    else:
        url, status = None, LINK_INVALID
    return Source(
        source_id=item.id,
        title=item.title,
        url=url,
        source_type=item.source_type,
        authors=list(item.authors),
        venue=item.venue or "",
        year=item.year,
        snippet=item.snippet or "",
        metadata={
            "engine": item.engine,
            "quality": item.quality,
            "cited_by": item.cited_by,
            "query": item.query,
        },
        link_status=status,
    )


def sources_from_store(store) -> list[Source]:
    return [source_from_evidence(item) for item in store.all()]


def source_by_id(store, source_id: str) -> Source | None:
    item = store.by_id(source_id) if store is not None else None
    if item is None:
        return None
    return source_from_evidence(item)


def public_link_label(source: Source) -> str:
    if source.link_status == LINK_VERIFIED and source.url:
        return "Verified source"
    return "Link unavailable"
