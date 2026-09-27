"""Support vs contradiction labelling from stored SerpApi hits."""

from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, Field

from core.grounding import flag_thin_evidence, ground_model
from core.llm import complete_json
from core.store import EvidenceItem, EvidenceStore
from core.textutil import keyword_hits

SUPPORT_CUES = (
    "outperform",
    "improves",
    "improvement",
    "achieves",
    "significant",
    "demonstrates",
    "state-of-the-art",
    "sota",
    "effective",
    "enables",
    "successfully",
)
CONTRA_CUES = (
    "fail",
    "fails",
    "limitation",
    "not significant",
    "does not",
    "cannot",
    "contradict",
    "overfit",
    "hype",
    "no improvement",
    "negative result",
    "replication",
    "confound",
    "bias",
    "does not beat",
    "underperform",
)

QUALITY_WEIGHT = {
    "peer_reviewed": 1.0,
    "news": 0.45,
    "repo": 0.55,
    "blog": 0.25,
    "web": 0.35,
    "other": 0.3,
}

SYSTEM = (
    "You classify evidence for a research claim. Use ONLY provided source IDs. "
    "Label each item supporting, contradicting, or neutral. Explain disagreements "
    "via data, method, or population — never via facts you were not given. "
    "Do not invent papers."
)


class StanceItem(BaseModel):
    source_id: str
    stance: str  # supporting | contradicting | neutral
    quality: str
    title: str = ""
    url: str = ""
    why: str
    weight: float = 0.3


class Disagreement(BaseModel):
    theme: str
    explanation: str
    source_ids: list[str] = Field(default_factory=list)


class ContradictionsReport(BaseModel):
    core_claim: str
    thin_evidence: bool = False
    confidence: float = 0.4
    supporting: list[StanceItem] = Field(default_factory=list)
    contradicting: list[StanceItem] = Field(default_factory=list)
    neutral: list[StanceItem] = Field(default_factory=list)
    disagreements: list[Disagreement] = Field(default_factory=list)
    balance_note: str = ""
    source_ids: list[str] = Field(default_factory=list)
    dropped_citations: list[str] = Field(default_factory=list)


def _stance_for(item: EvidenceItem) -> tuple[str, str]:
    blob = f"{item.title} {item.snippet}".lower()
    s = keyword_hits(blob, SUPPORT_CUES)
    c = keyword_hits(blob, CONTRA_CUES)
    if c > s and c > 0:
        return "contradicting", f"Contradiction cues in the retrieved snippet (hits={c})."
    if s > c and s > 0:
        return "supporting", f"Support cues in the retrieved snippet (hits={s})."
    return "neutral", "Snippet does not clearly support or refute the claim."


def heuristic_contradictions(abstract: str, store: EvidenceStore) -> ContradictionsReport:
    claim = abstract.strip().split(".")[0][:280]
    thin = flag_thin_evidence(store)
    buckets = {"supporting": [], "contradicting": [], "neutral": []}
    ids = []
    for item in store.all()[:40]:
        stance, why = _stance_for(item)
        weight = QUALITY_WEIGHT.get(item.quality, 0.3)
        row = StanceItem(
            source_id=item.id,
            stance=stance,
            quality=item.quality,
            title=item.title,
            url=item.url,
            why=why,
            weight=weight,
        )
        buckets[stance].append(row)
        ids.append(item.id)
    # Keep the most informative rows
    for k in buckets:
        buckets[k] = sorted(buckets[k], key=lambda r: -r.weight)[:8]
    sw = sum(x.weight for x in buckets["supporting"])
    cw = sum(x.weight for x in buckets["contradicting"])
    disagreements = []
    if buckets["supporting"] and buckets["contradicting"]:
        disagreements.append(
            Disagreement(
                theme="method vs. reporting venue",
                explanation=(
                    "Peer-reviewed Scholar hits and news/web hits in the store often disagree "
                    "because they use different evaluation settings, time windows, or populations. "
                    "Treat news-quality rows as weaker than Scholar papers."
                ),
                source_ids=[
                    buckets["supporting"][0].source_id,
                    buckets["contradicting"][0].source_id,
                ],
            )
        )
    if any(i.source_type == "github" for i in store.all()) and buckets["supporting"]:
        disagreements.append(
            Disagreement(
                theme="paper claim vs. build artefact",
                explanation=(
                    "A GitHub/dataset hit can look supportive because code exists, while the paper "
                    "snippet may still describe failures or limited populations."
                ),
                source_ids=[i.id for i in store.all() if i.source_type == "github"][:2],
            )
        )
    if not disagreements:
        disagreements.append(
            Disagreement(
                theme="insufficient contrast",
                explanation="The store does not contain a clear opposing pair; conclusions are tentative.",
                source_ids=ids[:2],
            )
        )
    note = (
        f"Weighted support {sw:.1f} vs contradiction {cw:.1f} "
        f"(peer-reviewed counts more than news or blogs)."
    )
    if thin:
        note += " Evidence is thin."
    conf = 0.3 if thin else min(0.8, 0.4 + 0.05 * min(len(ids), 8))
    return ContradictionsReport(
        core_claim=claim,
        thin_evidence=thin,
        confidence=round(conf, 2),
        supporting=buckets["supporting"],
        contradicting=buckets["contradicting"],
        neutral=buckets["neutral"][:8],
        disagreements=disagreements,
        balance_note=note,
        source_ids=ids[:20],
    )


def analyze_contradictions(
    abstract: str,
    store: EvidenceStore,
    *,
    use_llm: bool = False,
    llm_kwargs: dict[str, Any] | None = None,
    complete: Callable[..., ContradictionsReport] | None = None,
) -> ContradictionsReport:
    fallback = heuristic_contradictions(abstract, store)
    if not use_llm:
        return fallback
    fn = complete or complete_json
    user = (
        f"Abstract / claim:\n{abstract}\n\nEvidence:\n{store.to_llm_context()}\n"
        "Classify sources. Explain WHY they differ using only snippets."
    )
    try:
        report = fn(SYSTEM, user, ContradictionsReport, **(llm_kwargs or {}))
        report, dropped = ground_model(report, store)
        report.dropped_citations = dropped
        for group in (report.supporting, report.contradicting, report.neutral):
            for row in group:
                item = store.by_id(row.source_id)
                if item:
                    row.title = item.title
                    row.url = item.url
                    row.quality = item.quality
        report.thin_evidence = report.thin_evidence or fallback.thin_evidence
        return report
    except Exception:
        return fallback
