"""Three-agent debate grounded strictly in evidence-store IDs."""

from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, Field

from core.grounding import flag_thin_evidence, ground_model
from core.llm import complete_json
from core.store import EvidenceStore
from modules.contradictions import ContradictionsReport, heuristic_contradictions

SYSTEM = (
    "You run a debate. Advocate and Skeptic may cite ONLY evidence source_ids. "
    "If a point cannot be cited, drop it. Judge scores both and gives a verdict. "
    "Never invent papers, URLs, or quotes."
)


class DebateTurn(BaseModel):
    speaker: str  # Advocate | Skeptic | Judge
    text: str
    source_ids: list[str] = Field(default_factory=list)


class DebateReport(BaseModel):
    transcript: list[DebateTurn] = Field(default_factory=list)
    advocate_score: int = Field(ge=0, le=10, default=5)
    skeptic_score: int = Field(ge=0, le=10, default=5)
    verdict: str
    confidence: float = Field(ge=0, le=1, default=0.4)
    thin_evidence: bool = False
    source_ids: list[str] = Field(default_factory=list)
    dropped_citations: list[str] = Field(default_factory=list)


def _cite(ids: list[str]) -> str:
    return ", ".join(ids) if ids else "(no store id)"


def heuristic_debate(
    abstract: str,
    store: EvidenceStore,
    contradictions: ContradictionsReport | None = None,
) -> DebateReport:
    c = contradictions or heuristic_contradictions(abstract, store)
    thin = flag_thin_evidence(store) or c.thin_evidence
    adv_ids = [x.source_id for x in c.supporting[:3]]
    sk_ids = [x.source_id for x in c.contradicting[:3]] or [x.source_id for x in c.neutral[:2]]
    papers = store.filter(source_type="paper")
    paper_ids = [p.id for p in papers[:3]]

    adv_bits = []
    for row in c.supporting[:3]:
        adv_bits.append(f"{row.source_id} ({row.quality}): {row.title[:90]}. {row.why}")
    sk_bits = []
    for row in (c.contradicting or c.neutral)[:3]:
        sk_bits.append(f"{row.source_id} ({row.quality}): {row.title[:90]}. {row.why}")

    if not adv_bits:
        adv_bits.append("Store has no clearly supporting hits; Advocate cannot overclaim.")
    if not sk_bits:
        sk_bits.append("Store has no clearly contradicting hits; absence of critique is not proof.")

    transcript = [
        DebateTurn(
            speaker="Advocate",
            text=(
                f"Pursue this line. The closest retrieved hits already show related work rather than a dead end: "
                + " ".join(adv_bits)
                + f" Weighted support in the store is cited via {_cite(adv_ids or paper_ids)}."
            ),
            source_ids=adv_ids or paper_ids,
        ),
        DebateTurn(
            speaker="Skeptic",
            text=(
                "Hold. Several hits are news, blogs, or negative-leaning snippets, which are weaker than "
                "peer-reviewed papers and often describe failures, limits, or hype. "
                + " ".join(sk_bits)
                + f" See {_cite(sk_ids)}."
            ),
            source_ids=sk_ids,
        ),
        DebateTurn(
            speaker="Advocate",
            text=(
                "Those weaker sources should not veto a research agenda. Differentiation is still possible "
                f"if the author replicates the closest papers ({_cite(paper_ids)}) on a new population or metric "
                "instead of restating them."
            ),
            source_ids=paper_ids,
        ),
        DebateTurn(
            speaker="Skeptic",
            text=(
                f"Replication cost is unknown from this store. If GitHub/dataset coverage is thin, "
                f"build-on-ability is a risk. Thin evidence={thin}."
            ),
            source_ids=sk_ids[:1] + paper_ids[:1],
        ),
    ]

    sw = sum(x.weight for x in c.supporting)
    cw = sum(x.weight for x in c.contradicting)
    n_peer = sum(1 for x in store.all() if x.quality == "peer_reviewed")
    adv = int(round(min(9, 4 + sw / 2 + 0.2 * n_peer)))
    sk = int(round(min(9, 4 + cw / 2 + (1.5 if thin else 0))))
    if adv == sk:
        verdict = (
            "Split decision: the idea is worth a short replication study, not a large bet, "
            "until more retrieved evidence exists."
        )
    elif adv > sk:
        verdict = (
            "Conditional pursue: Scholar-weighted support outranks contradictions. "
            "Next step is a differentiation experiment against the closest papers."
        )
    else:
        verdict = (
            "Do not scale yet: contradicting or low-quality hits dominate. "
            "Tighten the claim or pick a narrower population."
        )
    ids = list(dict.fromkeys(adv_ids + sk_ids + paper_ids))
    conf = 0.28 if thin else min(0.75, 0.4 + 0.04 * n_peer)
    transcript.append(
        DebateTurn(
            speaker="Judge",
            text=(
                f"Advocate {adv}/10, Skeptic {sk}/10. {verdict} "
                f"Confidence {conf:.2f} because every turn is bound to store IDs {_cite(ids)}."
            ),
            source_ids=ids,
        )
    )
    return DebateReport(
        transcript=transcript,
        advocate_score=adv,
        skeptic_score=sk,
        verdict=verdict,
        confidence=round(conf, 2),
        thin_evidence=thin,
        source_ids=ids,
    )


def analyze_debate(
    abstract: str,
    store: EvidenceStore,
    contradictions: ContradictionsReport | None = None,
    *,
    use_llm: bool = False,
    llm_kwargs: dict[str, Any] | None = None,
    complete: Callable[..., DebateReport] | None = None,
) -> DebateReport:
    fallback = heuristic_debate(abstract, store, contradictions)
    if not use_llm:
        return fallback
    fn = complete or complete_json
    user = (
        f"Abstract:\n{abstract}\n\nEvidence:\n{store.to_llm_context()}\n"
        "Write Advocate / Skeptic / Judge turns. Cite source_ids only."
    )
    try:
        report = fn(SYSTEM, user, DebateReport, **(llm_kwargs or {}))
        report, dropped = ground_model(report, store)
        report.dropped_citations = dropped
        report.thin_evidence = report.thin_evidence or fallback.thin_evidence
        if not report.transcript:
            return fallback
        return report
    except Exception:
        return fallback
