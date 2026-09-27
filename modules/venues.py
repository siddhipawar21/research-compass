"""Conferences, workshops, grants — deadlines never invented."""

from __future__ import annotations

import re
from typing import Any, Callable

from pydantic import BaseModel, Field

from core.grounding import flag_thin_evidence, ground_model
from core.llm import complete_json
from core.store import EvidenceStore

DEADLINE_RE = re.compile(
    r"\b(?:deadline|due|closes|closing|submit by|submission)\b[^.]{0,40}?"
    r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+20\d{2}"
    r"|\d{4}-\d{2}-\d{2}"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+20\d{2}"
    r"|\d{1,2}/\d{1,2}/20\d{2})",
    re.IGNORECASE,
)

DATE_ONLY_RE = re.compile(
    r"\b(?:\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+20\d{2}"
    r"|\d{4}-\d{2}-\d{2}"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+20\d{2})\b",
    re.IGNORECASE,
)

INDIA_CUES = ("india", "indian", "serb", "dst ", "anrf", "csir", "ugc", "iit", "iiit", "iisc", "inrae", "dbt")

SYSTEM = (
    "Extract venues and grants from evidence only. If a deadline is not explicitly present "
    "in the snippet/title, set deadline to 'not found'. Never invent dates. Prefer India-relevant rows."
)


class VenueRow(BaseModel):
    source_id: str
    name: str
    kind: str  # conference | workshop | grant | fellowship | other
    india_relevant: bool = False
    deadline: str = "not found"
    url: str = ""
    note: str = ""


class VenuesReport(BaseModel):
    rows: list[VenueRow] = Field(default_factory=list)
    thin_evidence: bool = False
    confidence: float = 0.4
    summary: str = ""
    source_ids: list[str] = Field(default_factory=list)
    dropped_citations: list[str] = Field(default_factory=list)


def extract_deadline(text: str) -> str:
    blob = text or ""
    m = DEADLINE_RE.search(blob)
    if m:
        return m.group(1).strip()
    # Only accept a bare date if the word deadline/due appears somewhere nearby.
    if re.search(r"\b(deadline|due|cfp|submission)\b", blob, re.I):
        m2 = DATE_ONLY_RE.search(blob)
        if m2:
            return m2.group(0)
    return "not found"


def _kind(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ("fellowship", "fellow ")):
        return "fellowship"
    if any(w in t for w in ("grant", "serb", "anrf", "dst", "funding")):
        return "grant"
    if "workshop" in t:
        return "workshop"
    if any(w in t for w in ("conference", "cfp", "call for papers", "symposium")):
        return "conference"
    return "other"


def heuristic_venues(abstract: str, store: EvidenceStore) -> VenuesReport:
    thin = flag_thin_evidence(store)
    rows: list[VenueRow] = []
    for item in store.all():
        blob = f"{item.title} {item.snippet} {item.venue}"
        kind = _kind(blob)
        india = any(c in blob.lower() for c in INDIA_CUES)
        looks_venue = kind != "other" or item.source_type == "venue" or "cfp" in blob.lower()
        if not looks_venue:
            continue
        rows.append(
            VenueRow(
                source_id=item.id,
                name=item.title[:160],
                kind=kind if kind != "other" else ("venue" if item.source_type == "venue" else "other"),
                india_relevant=india,
                deadline=extract_deadline(blob),
                url=item.url,
                note=item.snippet[:180] or "No snippet.",
            )
        )
    rows.sort(key=lambda r: (not r.india_relevant, r.deadline == "not found"))
    ids = [r.source_id for r in rows]
    if not rows:
        thin = True
        summary = "No conference or grant-like hits were present in the retrieved sources."
    else:
        india_n = sum(1 for r in rows if r.india_relevant)
        summary = (
            f"{len(rows)} venue/grant-like hits; {india_n} look India-relevant. "
            "Deadlines are copied from snippets only; otherwise 'not found'."
        )
    conf = 0.25 if thin else 0.5
    return VenuesReport(
        rows=rows[:15],
        thin_evidence=thin,
        confidence=conf,
        summary=summary,
        source_ids=ids[:15],
    )


def analyze_venues(
    abstract: str,
    store: EvidenceStore,
    *,
    use_llm: bool = False,
    llm_kwargs: dict[str, Any] | None = None,
    complete: Callable[..., VenuesReport] | None = None,
) -> VenuesReport:
    fallback = heuristic_venues(abstract, store)
    if not use_llm:
        return fallback
    fn = complete or complete_json
    try:
        report = fn(
            SYSTEM,
            f"Abstract:\n{abstract}\n\nEvidence:\n{store.to_llm_context()}",
            VenuesReport,
            **(llm_kwargs or {}),
        )
        report, dropped = ground_model(report, store)
        report.dropped_citations = dropped
        # Force deadline honesty: if store text lacks a date, override LLM.
        for row in report.rows:
            item = store.by_id(row.source_id)
            if not item:
                row.deadline = "not found"
                continue
            row.url = item.url
            row.name = item.title[:160]
            extracted = extract_deadline(f"{item.title} {item.snippet} {item.venue}")
            if extracted == "not found":
                row.deadline = "not found"
            else:
                row.deadline = extracted
        report.rows = [r for r in report.rows if r.source_id]
        return report
    except Exception:
        return fallback
