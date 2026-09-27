"""Best-effort BibTeX from evidence-store fields only."""

from __future__ import annotations

import re

from core.store import EvidenceItem

UNKNOWN = {
    "author": "AUTHOR-UNKNOWN",
    "year": "YEAR-UNKNOWN",
    "venue": "VENUE-UNKNOWN",
    "title": "TITLE-UNKNOWN",
}


def _tex_escape(text: str) -> str:
    return (
        (text or "")
        .replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("$", "\\$")
        .replace("#", "\\#")
    )


def _cite_key(item: EvidenceItem) -> str:
    raw = (item.authors[0] if item.authors else "unk") + str(item.year or "nd") + item.id
    key = re.sub(r"[^A-Za-z0-9]+", "", raw)
    return key[:40] or item.id.replace("-", "")


def bibtex_entry(item: EvidenceItem) -> str:
    title = item.title.strip() if item.title and item.title != "Untitled result" else UNKNOWN["title"]
    if item.authors:
        author = " and ".join(a.strip() for a in item.authors if a.strip()) or UNKNOWN["author"]
    else:
        author = UNKNOWN["author"]
    year = str(item.year) if item.year else UNKNOWN["year"]
    venue = item.venue.strip() if item.venue else UNKNOWN["venue"]
    kind = "@article" if item.source_type == "paper" else "@misc"
    key = _cite_key(item)
    lines = [
        f"{kind}{{{key},",
        f"  title = {{{_tex_escape(title)}}},",
        f"  author = {{{_tex_escape(author)}}},",
        f"  year = {{{_tex_escape(year)}}},",
    ]
    if kind == "@article":
        lines.append(f"  journal = {{{_tex_escape(venue)}}},")
    else:
        lines.append(f"  howpublished = {{{_tex_escape(venue)}}},")
    if item.url:
        lines.append(f"  url = {{{_tex_escape(item.url)}}},")
    if item.cited_by is not None:
        lines.append(f"  note = {{cited_by {item.cited_by}}},")
    lines.append("}")
    return "\n".join(lines)


def bibtex_for_closest(items: list[EvidenceItem]) -> str:
    return "\n\n".join(bibtex_entry(i) for i in items if i)
