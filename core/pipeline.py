"""Run planning, SerpApi collection, and all analysis modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from core.config import Settings, load_settings
from core.planner import QueryPlan, plan_queries
from core.serp import SearchOutcome, SerpClient
from core.store import EvidenceStore
from modules.contradictions import ContradictionsReport, analyze_contradictions
from modules.debate import DebateReport, analyze_debate
from modules.experts import ExpertsReport, analyze_experts
from modules.novelty import NoveltyReport, analyze_novelty
from modules.radar import RadarReport, analyze_radar
from modules.reproducibility import ReproducibilityReport, analyze_reproducibility
from modules.venues import VenuesReport, analyze_venues

ProgressFn = Callable[[str, float], None]


@dataclass
class CompassReport:
    abstract: str
    mode: str
    sample_id: str | None
    plan: QueryPlan
    novelty: NoveltyReport
    contradictions: ContradictionsReport
    debate: DebateReport
    reproducibility: ReproducibilityReport
    radar: RadarReport
    experts: ExpertsReport
    venues: VenuesReport
    store: EvidenceStore
    searches: list[SearchOutcome] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def pursue_verdict(self) -> str:
        return self.debate.verdict


def execute_plan(client: SerpClient, store: EvidenceStore, plan: QueryPlan, progress: ProgressFn | None = None) -> list[SearchOutcome]:
    outcomes: list[SearchOutcome] = []
    n = max(1, len(plan.queries))
    for i, q in enumerate(plan.queries):
        if progress:
            progress(f"SerpApi {q.engine}: {q.purpose or q.q[:40]}", 0.1 + 0.45 * (i / n))
        params = dict(q.extra_params)
        if q.q:
            params.setdefault("q", q.q)
        if q.engine == "google_scholar_profiles" and "mauthors" not in params and q.q:
            params["mauthors"] = q.q
            params.pop("q", None)
        if q.engine == "google_trends":
            params.setdefault("data_type", "TIMESERIES")
        out = client.search(q.engine, **params)
        outcomes.append(out)
        if out.data and not out.error:
            query_label = params.get("q") or params.get("mauthors") or params.get("author_id") or ""
            store.ingest_search(out.engine, out.data, str(query_label))
    return outcomes


def run_analysis(
    abstract: str,
    store: EvidenceStore,
    *,
    use_llm: bool,
    settings: Settings,
    progress: ProgressFn | None = None,
) -> dict[str, Any]:
    llm_kwargs = {
        "api_key": settings.anthropic_api_key,
        "model": settings.anthropic_model,
        "max_retries": settings.llm_max_retries,
    }
    if progress:
        progress("Novelty", 0.62)
    novelty = analyze_novelty(abstract, store, use_llm=use_llm, llm_kwargs=llm_kwargs)
    if progress:
        progress("Contradictions", 0.70)
    contradictions = analyze_contradictions(abstract, store, use_llm=use_llm, llm_kwargs=llm_kwargs)
    if progress:
        progress("Debate", 0.78)
    debate = analyze_debate(abstract, store, contradictions, use_llm=use_llm, llm_kwargs=llm_kwargs)
    if progress:
        progress("Reproducibility", 0.84)
    repro = analyze_reproducibility(abstract, store, use_llm=use_llm, llm_kwargs=llm_kwargs)
    if progress:
        progress("Experts", 0.88)
    experts = analyze_experts(abstract, store, use_llm=use_llm, llm_kwargs=llm_kwargs)
    if progress:
        progress("Venues", 0.92)
    venues = analyze_venues(abstract, store, use_llm=use_llm, llm_kwargs=llm_kwargs)
    if progress:
        progress("Topic radar", 0.96)
    radar = analyze_radar(abstract, store, use_llm=use_llm, llm_kwargs=llm_kwargs)
    return {
        "novelty": novelty,
        "contradictions": contradictions,
        "debate": debate,
        "reproducibility": repro,
        "experts": experts,
        "venues": venues,
        "radar": radar,
    }


def run_compass(
    abstract: str,
    *,
    mode: str,
    client: SerpClient,
    store: EvidenceStore,
    settings: Settings | None = None,
    sample_id: str | None = None,
    use_llm: bool | None = None,
    preset_plan: QueryPlan | None = None,
    progress: ProgressFn | None = None,
) -> CompassReport:
    settings = settings or load_settings()
    if use_llm is None:
        use_llm = mode == "live" and settings.has_llm
    if progress:
        progress("Planning queries", 0.05)
    plan = preset_plan or plan_queries(abstract, use_llm=use_llm, llm_kwargs={
        "api_key": settings.anthropic_api_key,
        "model": settings.anthropic_model,
        "max_retries": settings.llm_max_retries,
    })
    client.reset_run()
    store.new_run()
    searches = execute_plan(client, store, plan, progress=progress)
    notes = list(client.meter.messages)
    if len(store.all()) == 0:
        notes.append("No evidence items were stored. The report will be low-confidence.")
    parts = run_analysis(abstract, store, use_llm=use_llm, settings=settings, progress=progress)
    if progress:
        progress("Done", 1.0)
    return CompassReport(
        abstract=abstract,
        mode=mode,
        sample_id=sample_id,
        plan=plan,
        store=store,
        searches=searches,
        notes=notes,
        **parts,
    )
