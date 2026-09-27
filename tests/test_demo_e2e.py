"""Demo-mode end-to-end using fixtures and no network / no API keys."""

from __future__ import annotations

from pathlib import Path

from core.config import load_settings
from core.demo import load_samples, match_sample, plan_from_fixtures, preload_client
from core.pipeline import run_compass
from core.report import report_to_markdown
from core.serp import SerpClient
from core.store import EvidenceStore


def test_demo_e2e_three_samples(tmp_path: Path):
    settings = load_settings()
    samples = load_samples()
    assert len(samples) >= 2
    for sample in samples:
        client = SerpClient("", tmp_path / f"{sample.id}.sqlite", max_searches=20)
        n = preload_client(client, sample)
        assert n >= 8
        store = EvidenceStore()
        report = run_compass(
            sample.abstract,
            mode="demo",
            client=client,
            store=store,
            settings=settings,
            sample_id=sample.id,
            use_llm=False,
            preset_plan=plan_from_fixtures(sample),
        )
        assert client.meter.used_this_run == 0
        assert client.meter.cache_hits_this_run == n
        titles = [i.title.strip().lower() for i in store.all() if i.title]
        assert len(titles) == len(set(titles)), f"duplicate titles in {sample.id}: {titles}"
        assert 0 <= report.novelty.score <= 100
        assert report.novelty.closest_works
        assert all(store.by_id(w.source_id) for w in report.novelty.closest_works)
        assert report.debate.transcript
        for turn in report.debate.transcript:
            for sid in turn.source_ids:
                assert store.by_id(sid), f"ungrounded {sid}"
        md = report_to_markdown(report)
        assert "Novelty" in md
        assert "SRC-001" in md
        for row in report.venues.rows:
            if row.deadline != "not found":
                item = store.by_id(row.source_id)
                blob = f"{item.title} {item.snippet}"
                assert "2026" in blob or "deadline" in blob.lower() or "due" in blob.lower()


def test_match_sample_fuzzy():
    samples = load_samples()
    s = match_sample("graph neural monsoon rainfall Maharashtra Kerala flood", samples)
    assert s is not None
    assert s.id == "gnn_climate"
