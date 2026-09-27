"""Query planner: 8–12 SerpApi searches tagged by engine."""

from __future__ import annotations

import re
from typing import Callable

from pydantic import BaseModel, Field, field_validator

from core.config import ENGINE_ALIASES, ALLOWED_ENGINES
from core.llm import complete_json


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
    "toward",
    "towards",
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
}


class PlannedQuery(BaseModel):
    engine: str
    q: str
    purpose: str = ""
    extra_params: dict[str, str] = Field(default_factory=dict)

    @field_validator("engine")
    @classmethod
    def map_engine(cls, v: str) -> str:
        key = (v or "").strip().lower()
        mapped = ENGINE_ALIASES.get(key, key)
        if mapped not in ALLOWED_ENGINES:
            raise ValueError(f"unsupported engine {v}")
        return mapped


class QueryPlan(BaseModel):
    queries: list[PlannedQuery] = Field(min_length=4, max_length=16)
    core_claim: str = ""
    keyphrases: list[str] = Field(default_factory=list)


def keyphrases_from_abstract(abstract: str, n: int = 8) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z\-]{3,}", abstract.lower())
    freq: dict[str, int] = {}
    for w in words:
        if w in STOP:
            continue
        freq[w] = freq.get(w, 0) + 1
    ranked = sorted(freq, key=lambda w: (-freq[w], w))
    return ranked[:n]


def heuristic_plan(abstract: str) -> QueryPlan:
    keys = keyphrases_from_abstract(abstract)
    phrase = " ".join(keys[:5]) or "research idea"
    core = abstract.strip().split(".")[0][:240]
    india = "india indian" if any(x in abstract.lower() for x in ("india", "indian", "bharat", "hindi")) else ""
    queries = [
        PlannedQuery(engine="google_scholar", q=phrase, purpose="closest papers", extra_params={"num": "10", "hl": "en"}),
        PlannedQuery(
            engine="google_scholar",
            q=phrase,
            purpose="recent papers",
            extra_params={"num": "10", "hl": "en", "as_ylo": "2022"},
        ),
        PlannedQuery(
            engine="google_scholar",
            q=f"{phrase} review OR survey",
            purpose="surveys",
            extra_params={"num": "8", "hl": "en"},
        ),
        PlannedQuery(
            engine="google",
            q=f"{phrase} site:github.com",
            purpose="code",
        ),
        PlannedQuery(
            engine="google",
            q=f"{phrase} dataset OR benchmark site:huggingface.co OR site:paperswithcode.com OR site:kaggle.com",
            purpose="datasets",
        ),
        PlannedQuery(
            engine="google_news",
            q=phrase,
            purpose="news coverage",
            extra_params={"hl": "en", "gl": "in"},
        ),
        PlannedQuery(
            engine="google_trends",
            q=keys[0] if keys else phrase,
            purpose="interest over time",
            extra_params={"data_type": "TIMESERIES", "date": "today 5-y"},
        ),
        PlannedQuery(
            engine="google_scholar_profiles",
            q="",
            purpose="active authors",
            extra_params={"mauthors": phrase[:80], "hl": "en"},
        ),
        PlannedQuery(
            engine="google",
            q=f"{phrase} conference OR workshop CFP 2026 OR 2027",
            purpose="venues",
        ),
        PlannedQuery(
            engine="google",
            q=f"{phrase} {india} grant OR fellowship OR SERB OR DST OR ANRF OR CSIR deadline".strip(),
            purpose="india grants",
        ),
        PlannedQuery(
            engine="google",
            q=f"{phrase} limitation OR fails OR contradictory OR replication",
            purpose="contradictions",
        ),
        PlannedQuery(
            engine="google_scholar",
            q=f"{core[:80]}",
            purpose="claim-like titles",
            extra_params={"num": "8", "hl": "en"},
        ),
    ]
    # Dedup (engine, q)
    seen = set()
    uniq: list[PlannedQuery] = []
    for q in queries:
        sig = (q.engine, q.q, tuple(sorted(q.extra_params.items())))
        if sig in seen or not (q.q or q.extra_params):
            continue
        seen.add(sig)
        uniq.append(q)
    return QueryPlan(queries=uniq[:12], core_claim=core, keyphrases=keys)


SYSTEM = (
    "You plan SerpApi searches for a research-idea audit. "
    "Every query must be executable on one of: google_scholar, google, google_news, "
    "google_trends, google_scholar_profiles. "
    "Prefer 8-12 targeted queries. Include site:github.com, datasets, news, trends, "
    "venues/grants (prefer India-relevant), and contradiction-seeking queries. "
    "Do not invent paper titles. Queries only."
)


def plan_queries(
    abstract: str,
    *,
    complete: Callable[..., QueryPlan] | None = None,
    use_llm: bool = False,
    llm_kwargs: dict | None = None,
) -> QueryPlan:
    if not use_llm:
        return heuristic_plan(abstract)
    fn = complete or complete_json
    try:
        plan = fn(
            SYSTEM,
            f"Research idea / abstract:\n{abstract}",
            QueryPlan,
            **(llm_kwargs or {}),
        )
        if len(plan.queries) < 8:
            # Fill from heuristic to keep coverage.
            extra = heuristic_plan(abstract).queries
            have = {(q.engine, q.q) for q in plan.queries}
            for q in extra:
                if (q.engine, q.q) not in have:
                    plan.queries.append(q)
                if len(plan.queries) >= 10:
                    break
        return plan
    except Exception:
        return heuristic_plan(abstract)
