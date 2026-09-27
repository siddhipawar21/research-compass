"""GitHub, datasets, and reimplementations from the evidence store."""

from __future__ import annotations

from typing import Any, Callable
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from core.grounding import flag_thin_evidence, ground_model
from core.llm import complete_json
from core.store import EvidenceStore

SYSTEM = (
    "You assess reproducibility from SerpApi hits only. List GitHub repos, datasets, "
    "and reimplementations with source_ids. Rate Low/Med/High. Never invent links."
)


class Artifact(BaseModel):
    source_id: str
    kind: str  # github | dataset | reimplementation | discussion
    title: str = ""
    url: str = ""
    what_it_offers: str
    missing: str = ""


class ReproducibilityReport(BaseModel):
    rating: str  # Low | Med | High
    confidence: float = 0.4
    thin_evidence: bool = False
    summary: str
    artifacts: list[Artifact] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    dropped_citations: list[str] = Field(default_factory=list)


def _kind_from(item) -> str | None:
    host = urlparse(item.url or "").netloc.lower()
    if item.source_type == "github" or "github.com" in host:
        return "github"
    if item.source_type == "dataset" or any(
        h in host for h in ("huggingface.co", "kaggle.com", "zenodo.org", "figshare")
    ):
        return "dataset"
    if item.source_type == "reimplementation" or "paperswithcode.com" in host:
        return "reimplementation"
    if any(h in host for h in ("reddit.com", "stackoverflow.com", "discourse")):
        return "discussion"
    title = (item.title + " " + item.snippet).lower()
    if "github" in title:
        return "github"
    if "dataset" in title or "benchmark" in title:
        return "dataset"
    return None


def heuristic_reproducibility(abstract: str, store: EvidenceStore) -> ReproducibilityReport:
    thin = flag_thin_evidence(store)
    arts: list[Artifact] = []
    for item in store.all():
        kind = _kind_from(item)
        if not kind:
            continue
        missing = ""
        if kind == "github" and "readme" not in (item.snippet or "").lower():
            missing = "Snippet does not confirm a README, license, or tests."
        arts.append(
            Artifact(
                source_id=item.id,
                kind=kind,
                title=item.title,
                url=item.url,
                what_it_offers=item.snippet[:220] or "Retrieved hit without a snippet.",
                missing=missing,
            )
        )
    kinds = {a.kind for a in arts}
    if {"github", "dataset"} <= kinds:
        rating = "High"
    elif "github" in kinds or "dataset" in kinds or "reimplementation" in kinds:
        rating = "Med"
    else:
        rating = "Low"
    missing = []
    if "github" not in kinds:
        missing.append("No GitHub repository appeared in the retrieved sources.")
    if "dataset" not in kinds:
        missing.append("No dataset / Hugging Face / Kaggle hit appeared in the store.")
    if "reimplementation" not in kinds:
        missing.append("No Papers with Code hit appeared in the store.")
    if thin:
        missing.append("Overall evidence is thin, so this rating is weakly supported.")
    summary = (
        f"Build-on-ability is {rating} based on {len(arts)} code/data/discussion hits "
        f"in the evidence store."
    )
    conf = 0.3 if thin or rating == "Low" else 0.55 if rating == "Med" else 0.7
    return ReproducibilityReport(
        rating=rating,
        confidence=round(conf, 2),
        thin_evidence=thin,
        summary=summary,
        artifacts=arts[:12],
        missing=missing,
        source_ids=[a.source_id for a in arts[:12]],
    )


def analyze_reproducibility(
    abstract: str,
    store: EvidenceStore,
    *,
    use_llm: bool = False,
    llm_kwargs: dict[str, Any] | None = None,
    complete: Callable[..., ReproducibilityReport] | None = None,
) -> ReproducibilityReport:
    fallback = heuristic_reproducibility(abstract, store)
    if not use_llm:
        return fallback
    fn = complete or complete_json
    try:
        report = fn(
            SYSTEM,
            f"Abstract:\n{abstract}\n\nEvidence:\n{store.to_llm_context()}",
            ReproducibilityReport,
            **(llm_kwargs or {}),
        )
        report, dropped = ground_model(report, store)
        report.dropped_citations = dropped
        for a in report.artifacts:
            item = store.by_id(a.source_id)
            if item:
                a.title = item.title
                a.url = item.url
        report.artifacts = [a for a in report.artifacts if a.source_id]
        return report
    except Exception:
        return fallback
