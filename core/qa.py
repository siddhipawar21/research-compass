"""Grounded Q&A over the current Research Compass report only."""

from __future__ import annotations

import re
from typing import Callable

from pydantic import BaseModel, Field

from core.config import Settings, load_settings
from core.llm import complete_json
from core.pipeline import CompassReport
from core.store import EvidenceStore
from core.textutil import overlap_score, tokens

SRC_RE = re.compile(r"\bSRC-\d{3}\b", re.I)
UNKNOWN = "I don't have enough evidence in this report to answer that."
DROPPED_NOTE = " (a claimed source was removed because it did not match the report's evidence)"

SYSTEM = (
    "Answer only using the evidence and report data provided below. "
    "If the answer is not in this data, say you don't have that information in the report. "
    "Every factual claim must cite a source ID from the data provided; "
    "never invent a source ID, paper, or number that is not in it."
)


class QAAnswer(BaseModel):
    answer: str
    cited_source_ids: list[str] = Field(default_factory=list)


def _kind(item) -> str:
    t = (item.source_type or "").lower()
    return {
        "paper": "paper",
        "github": "github",
        "dataset": "dataset",
        "news": "news",
        "venue": "venue",
        "author": "author",
        "trends": "trend",
        "reimplementation": "github",
        "web": "web",
    }.get(t, t or "other")


def _report_context(report: CompassReport) -> str:
    store: EvidenceStore = report.store
    lines = [
        f"Abstract:\n{report.abstract}",
        f"Novelty score: {report.novelty.score} (confidence {report.novelty.confidence}). {report.novelty.summary}",
        f"Verdict: {report.debate.verdict}",
        f"Radar: {report.radar.label}. {report.radar.reasoning}",
        f"Reproducibility: {report.reproducibility.rating}. {report.reproducibility.summary}",
        "Debate transcript:",
    ]
    for turn in report.debate.transcript:
        lines.append(f"- {turn.speaker}: {turn.text} ids={turn.source_ids}")
    lines.append("Venues:")
    for row in report.venues.rows:
        lines.append(f"- {row.source_id} {row.name} kind={row.kind} india={row.india_relevant} deadline={row.deadline}")
    lines.append("Evidence store:")
    stance_by_id = {}
    for row in report.contradictions.supporting:
        stance_by_id[row.source_id] = "supporting"
    for row in report.contradictions.contradicting:
        stance_by_id[row.source_id] = "contradicting"
    for row in report.contradictions.neutral:
        stance_by_id[row.source_id] = "neutral"
    for item in store.all():
        lines.append(
            f"[{item.id}] kind={_kind(item)} stance={stance_by_id.get(item.id, 'n/a')} "
            f"year={item.year} title={item.title}\n  snippet={item.snippet[:280]}"
        )
    return "\n".join(lines)


def _ground(answer: QAAnswer, store: EvidenceStore) -> QAAnswer:
    known = store.ids()
    keep, dropped = [], []
    for sid in answer.cited_source_ids:
        key = sid.upper() if sid.upper().startswith("SRC-") else sid
        if key in known:
            keep.append(key)
        elif sid in known:
            keep.append(sid)
        else:
            dropped.append(sid)
    answer.cited_source_ids = keep
    if dropped:
        answer.answer = answer.answer.rstrip() + DROPPED_NOTE
    return answer


def _fallback(question: str, report: CompassReport) -> QAAnswer:
    q = (question or "").strip()
    store = report.store
    mentioned = [m.upper() for m in SRC_RE.findall(q)]
    if mentioned:
        bits = []
        ids = []
        for sid in mentioned:
            item = store.by_id(sid)
            if not item:
                continue
            bits.append(f"{sid} ({_kind(item)}): {item.title}. {item.snippet[:240]}")
            ids.append(sid)
        if bits:
            return QAAnswer(answer=" ".join(bits), cited_source_ids=ids)
        return QAAnswer(answer=UNKNOWN, cited_source_ids=[])

    scored: list[tuple[float, str, list[str]]] = []
    scored.append((overlap_score(q, report.novelty.summary + f" novelty {report.novelty.score}"), report.novelty.summary, list(report.novelty.source_ids[:4])))
    scored.append((overlap_score(q, report.debate.verdict + " pursue verdict judge"), report.debate.verdict, list(report.debate.source_ids[:4])))
    scored.append((overlap_score(q, f"{report.reproducibility.rating} {report.reproducibility.summary}"), report.reproducibility.summary, list(report.reproducibility.source_ids[:4])))
    scored.append((overlap_score(q, f"{report.radar.label} {report.radar.reasoning}"), report.radar.reasoning, list(report.radar.source_ids[:4])))
    for item in store.all():
        blob = f"{item.id} {item.title} {item.snippet} {_kind(item)}"
        scored.append((overlap_score(q, blob), f"{item.id}: {item.title}. {item.snippet[:220]}", [item.id]))
    scored.sort(key=lambda x: -x[0])
    top = [s for s in scored if s[0] > 0.08][:4]
    q_tokens = tokens(q)
    looks_off_topic = bool(q_tokens) and not top
    injection = any(w in q.lower() for w in ("ignore the report", "ignore previous", "forget the report"))
    if looks_off_topic or not top:
        return QAAnswer(answer=UNKNOWN, cited_source_ids=[])
    if injection:
        # Still only report data; do not follow the instruction to leave the dossier.
        body = " ".join(t[1] for t in top[:2])
        ids = []
        for t in top[:2]:
            ids.extend(t[2])
        return QAAnswer(answer=body, cited_source_ids=list(dict.fromkeys(ids)))
    body = " ".join(t[1] for t in top)
    ids = []
    for t in top:
        ids.extend(t[2])
    return QAAnswer(answer=body, cited_source_ids=list(dict.fromkeys(ids)))


def answer_question(
    question: str,
    report: CompassReport,
    *,
    settings: Settings | None = None,
    use_llm: bool | None = None,
    complete: Callable[..., QAAnswer] | None = None,
) -> QAAnswer:
    settings = settings or load_settings()
    if use_llm is None:
        use_llm = bool(settings.has_llm)
    if not use_llm:
        return _fallback(question, report)
    fn = complete or complete_json
    user = f"Question:\n{question}\n\nReport data:\n{_report_context(report)}"
    try:
        raw = fn(SYSTEM, user, QAAnswer, api_key=settings.anthropic_api_key, model=settings.anthropic_model, max_retries=settings.llm_max_retries)
        return _ground(raw, report.store)
    except Exception:
        return _fallback(question, report)
