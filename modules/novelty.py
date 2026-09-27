"""Novelty module: score and closest existing works from the evidence store."""

from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, Field

from core.grounding import flag_thin_evidence, ground_model
from core.llm import complete_json
from core.store import EvidenceItem, EvidenceStore
from core.textutil import overlap_score

SYSTEM = (
    "You are a research novelty auditor. Use ONLY the evidence items provided. "
    "Every closest work must use a real source_id. Never invent papers or URLs. "
    "If evidence is thin, say so and lower confidence. Score 0 = already done, 100 = highly novel given this evidence."
)


class ClosestWork(BaseModel):
    source_id: str
    title: str
    similarity_reason: str
    overlap_notes: str = ""
    cited_by: int | None = None
    year: int | None = None
    url: str = ""


class NoveltyReport(BaseModel):
    score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    thin_evidence: bool = False
    summary: str
    closest_works: list[ClosestWork] = Field(default_factory=list)
    differentiation: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    dropped_citations: list[str] = Field(default_factory=list)


def _papers(store: EvidenceStore) -> list[EvidenceItem]:
    papers = store.filter(source_type="paper")
    if papers:
        return papers
    return [i for i in store.all() if i.source_type in {"paper", "web", "news"}]


def heuristic_novelty(abstract: str, store: EvidenceStore) -> NoveltyReport:
    thin = flag_thin_evidence(store)
    papers = _papers(store)
    ranked: list[tuple[float, EvidenceItem]] = []
    for item in papers:
        blob = f"{item.title} {item.snippet} {' '.join(item.authors)}"
        ranked.append((overlap_score(abstract, blob), item))
    ranked.sort(key=lambda x: (-x[0], -(x[1].cited_by or 0)))
    top = ranked[:5]
    max_sim = top[0][0] if top else 0.0
    n = len(papers)
    cites = max((p.cited_by or 0) for p in papers) if papers else 0
    score = int(round(100 - 45 * max_sim - min(25, n * 1.6) - min(15, (cites**0.5))))
    if thin:
        score = min(92, score + 8)
    score = max(5, min(95, score))
    closest = []
    ids = []
    for sim, item in top:
        ids.append(item.id)
        closest.append(
            ClosestWork(
                source_id=item.id,
                title=item.title,
                similarity_reason=(
                    f"Lexical overlap {sim:.2f} with the abstract"
                    + (f"; cited-by {item.cited_by}" if item.cited_by else "")
                    + "."
                ),
                overlap_notes=item.snippet[:240] or "No snippet in the retrieved hit.",
                cited_by=item.cited_by,
                year=item.year,
                url=item.url,
            )
        )
    diffs: list[str] = []
    if top:
        diffs.append(
            f"State a setting, population, or modality that {top[0][1].id} does not cover, "
            "and evaluate on that slice rather than restating its claim."
        )
        diffs.append(
            "Publish a replication table against the closest Scholar hits (same metrics, same years) "
            "before claiming superiority."
        )
    else:
        diffs.append("This report has no close papers; run a full literature search before treating novelty as high.")
    if any(i.source_type == "github" for i in store.all()):
        diffs.append("If code already exists in the store, differentiate on evaluation protocol, not another repo.")
    summary = (
        f"Novelty is scored {score}/100 from {n} paper-like retrieved hits "
        f"(max similarity {max_sim:.2f}, max cited-by {cites})."
    )
    if thin:
        summary += " Evidence is thin, so this score is weakly supported."
    conf = 0.35 if thin else min(0.85, 0.45 + 0.03 * n)
    return NoveltyReport(
        score=score,
        confidence=round(conf, 2),
        thin_evidence=thin,
        summary=summary,
        closest_works=closest,
        differentiation=diffs,
        source_ids=ids,
    )


def analyze_novelty(
    abstract: str,
    store: EvidenceStore,
    *,
    use_llm: bool = False,
    llm_kwargs: dict[str, Any] | None = None,
    complete: Callable[..., NoveltyReport] | None = None,
) -> NoveltyReport:
    fallback = heuristic_novelty(abstract, store)
    if not use_llm:
        return fallback
    fn = complete or complete_json
    user = (
        f"Abstract:\n{abstract}\n\nEvidence:\n{store.to_llm_context()}\n\n"
        "Score novelty of the abstract relative ONLY to these hits. "
        "List up to 5 closest works with source_id."
    )
    try:
        report = fn(SYSTEM, user, NoveltyReport, **(llm_kwargs or {}))
        report, dropped = ground_model(report, store)
        report.dropped_citations = dropped
        report.thin_evidence = report.thin_evidence or fallback.thin_evidence
        # Fill URLs/titles from store so the LLM cannot invent them.
        fixed = []
        for w in report.closest_works:
            item = store.by_id(w.source_id)
            if not item:
                continue
            w.title = item.title
            w.url = item.url
            w.year = item.year
            w.cited_by = item.cited_by
            fixed.append(w)
        report.closest_works = fixed[:5]
        report.source_ids = [w.source_id for w in report.closest_works]
        return report
    except Exception:
        return fallback
