"""Small text helpers used by planners and analysis modules."""

from __future__ import annotations

import math
import re

TOKEN_RE = re.compile(r"[a-z][a-z0-9\-]{2,}")
STOP = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "using",
    "based",
    "a",
    "an",
    "of",
    "in",
    "on",
    "to",
    "we",
    "our",
    "is",
    "are",
    "by",
    "or",
    "via",
    "than",
    "then",
    "its",
    "their",
    "have",
    "has",
    "been",
    "were",
    "was",
    "can",
    "may",
    "also",
    "such",
    "which",
    "these",
    "those",
    "paper",
    "study",
    "results",
    "method",
    "approach",
    "propose",
    "proposed",
    "show",
    "shown",
}


def tokens(text: str) -> set[str]:
    return {t for t in TOKEN_RE.findall((text or "").lower()) if t not in STOP}


def overlap_score(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / math.sqrt(len(ta) * len(tb))


def keyword_hits(text: str, words: tuple[str, ...]) -> int:
    blob = (text or "").lower()
    return sum(1 for w in words if w in blob)
