"""Active authors and labs from Scholar hits and profile searches."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from pydantic import BaseModel, Field

from core.grounding import flag_thin_evidence, ground_model
from core.llm import complete_json
from core.store import EvidenceStore

SYSTEM = (
    "List experts from evidence only. Use source_ids for papers and profiles. "
    "Draft a short intro email to one expert using only facts in the store. Never invent affiliations."
)


class Expert(BaseModel):
    name: str
    affiliation: str = ""
    why_read: str
    source_ids: list[str] = Field(default_factory=list)
    paper_titles: list[str] = Field(default_factory=list)
    profile_url: str = ""


class ExpertsReport(BaseModel):
    who_to_read_first: list[Expert] = Field(default_factory=list)
    labs: list[str] = Field(default_factory=list)
    intro_email: str = ""
    email_target: str = ""
    thin_evidence: bool = False
    confidence: float = 0.4
    source_ids: list[str] = Field(default_factory=list)
    dropped_citations: list[str] = Field(default_factory=list)


def heuristic_experts(abstract: str, store: EvidenceStore) -> ExpertsReport:
    thin = flag_thin_evidence(store)
    papers_by_author: dict[str, list] = defaultdict(list)
    for item in store.filter(source_type="paper"):
        for name in item.authors:
            if name and name.lower() not in {"et al", "et al."}:
                papers_by_author[name].append(item)
    profiles = store.filter(source_type="author")
    profile_by_name = {p.title: p for p in profiles}

    scored = []
    for name, items in papers_by_author.items():
        cites = sum(i.cited_by or 0 for i in items)
        scored.append((len(items), cites, name, items))
    scored.sort(reverse=True)
    experts: list[Expert] = []
    ids: list[str] = []
    for _, _, name, items in scored[:8]:
        ids.extend(i.id for i in items[:2])
        prof = profile_by_name.get(name)
        aff = ""
        url = ""
        if prof:
            aff = prof.snippet or prof.venue
            url = prof.url
            ids.append(prof.id)
        experts.append(
            Expert(
                name=name,
                affiliation=aff,
                why_read=f"Appears on {len(items)} Scholar hit(s) in the store, e.g. {items[0].title[:80]}.",
                source_ids=[i.id for i in items[:3]] + ([prof.id] if prof else []),
                paper_titles=[i.title for i in items[:3]],
                profile_url=url,
            )
        )
    for p in profiles:
        if all(p.title != e.name for e in experts):
            experts.append(
                Expert(
                    name=p.title,
                    affiliation=p.snippet or p.venue,
                    why_read="Google Scholar profile hit for this topic.",
                    source_ids=[p.id],
                    paper_titles=[],
                    profile_url=p.url,
                )
            )
            ids.append(p.id)
        if len(experts) >= 8:
            break

    labs = []
    for e in experts:
        if e.affiliation:
            labs.append(e.affiliation.split(",")[0][:80])
    labs = list(dict.fromkeys(labs))[:6]

    target = experts[0] if experts else None
    if target:
        email = (
            f"Subject: Question on {target.paper_titles[0][:70] if target.paper_titles else 'your related work'}\n\n"
            f"Dear {target.name},\n\n"
            f"I read the work indexed as {target.source_ids[0]} in a Scholar search "
            f"(\"{target.paper_titles[0] if target.paper_titles else target.name}\"). "
            "I am exploring a closely related idea and would value 15 minutes on evaluation pitfalls "
            "you would avoid in a follow-on study.\n\nThank you,\n[Your name]"
        )
        email_target = target.name
    else:
        email = "No author names were present in the retrieved sources, so an email cannot be grounded."
        email_target = ""
        thin = True
    conf = 0.3 if thin or not experts else min(0.7, 0.35 + 0.05 * len(experts))
    return ExpertsReport(
        who_to_read_first=experts[:6],
        labs=labs,
        intro_email=email,
        email_target=email_target,
        thin_evidence=thin,
        confidence=round(conf, 2),
        source_ids=list(dict.fromkeys(ids)),
    )


def analyze_experts(
    abstract: str,
    store: EvidenceStore,
    *,
    use_llm: bool = False,
    llm_kwargs: dict[str, Any] | None = None,
    complete: Callable[..., ExpertsReport] | None = None,
) -> ExpertsReport:
    fallback = heuristic_experts(abstract, store)
    if not use_llm:
        return fallback
    fn = complete or complete_json
    try:
        report = fn(
            SYSTEM,
            f"Abstract:\n{abstract}\n\nEvidence:\n{store.to_llm_context()}",
            ExpertsReport,
            **(llm_kwargs or {}),
        )
        report, dropped = ground_model(report, store)
        report.dropped_citations = dropped
        if not report.who_to_read_first:
            return fallback
        return report
    except Exception:
        return fallback
