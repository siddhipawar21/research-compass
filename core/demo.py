"""Demo fixtures: sample abstracts + pre-saved SerpApi payloads."""

from __future__ import annotations

import json
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from core.planner import PlannedQuery, QueryPlan
from core.serp import SerpClient

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo_data"


@dataclass
class Sample:
    id: str
    title: str
    abstract: str
    fixture_file: str


def load_samples() -> list[Sample]:
    path = DEMO_DIR / "samples.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Sample(**row) for row in data]


def match_sample(abstract: str, samples: list[Sample] | None = None) -> Sample | None:
    samples = samples or load_samples()
    text = " ".join((abstract or "").split()).lower()
    if not text:
        return None
    best: tuple[float, Sample | None] = (0.0, None)
    for s in samples:
        cand = " ".join(s.abstract.split()).lower()
        if text == cand or text in cand or cand in text:
            return s
        r = SequenceMatcher(None, text[:600], cand[:600]).ratio()
        if r > best[0]:
            best = (r, s)
    if best[0] >= 0.42:
        return best[1]
    return samples[0]


def exact_sample(abstract: str, samples: list[Sample] | None = None) -> Sample | None:
    samples = samples or load_samples()
    text = " ".join((abstract or "").split()).lower()
    if not text:
        return None
    for s in samples:
        if text == " ".join(s.abstract.split()).lower():
            return s
    return None


def _blank_fixture_links(obj):
    """Synthetic fixtures must not deep-link to unrelated real papers."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in {"link", "url"} and isinstance(v, str) and v.startswith(("http://", "https://")):
                out[k] = ""
            else:
                out[k] = _blank_fixture_links(v)
        return out
    if isinstance(obj, list):
        return [_blank_fixture_links(x) for x in obj]
    return obj


def load_fixture_searches(sample: Sample) -> list[dict]:
    path = DEMO_DIR / sample.fixture_file
    data = json.loads(path.read_text(encoding="utf-8"))
    return _blank_fixture_links(data)


def preload_client(client: SerpClient, sample: Sample) -> int:
    rows = load_fixture_searches(sample)
    for row in rows:
        engine = row["engine"]
        params = row.get("params") or {}
        client.cache.preload_fixture(engine, params, row.get("response") or {})
    return len(rows)


def plan_from_fixtures(sample: Sample) -> QueryPlan:
    queries: list[PlannedQuery] = []
    for row in load_fixture_searches(sample):
        params = {k: str(v) for k, v in (row.get("params") or {}).items()}
        q = params.pop("q", "")
        queries.append(
            PlannedQuery(
                engine=row["engine"],
                q=q,
                purpose=row.get("purpose") or "",
                extra_params=params,
            )
        )
    return QueryPlan(queries=queries, core_claim=sample.abstract.split(".")[0][:240], keyphrases=[])
