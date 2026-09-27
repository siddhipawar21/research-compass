import re
from pathlib import Path

from core.bibtex import UNKNOWN, bibtex_entry, bibtex_for_closest
from core.config import load_settings
from core.demo import load_samples, plan_from_fixtures, preload_client
from core.history import RunHistory, SavedReport, relative_time
from core.pipeline import run_compass
from core.serp import SearchCache, SerpClient
from core.store import EvidenceItem, EvidenceStore


def _run(tmp_path: Path, sample_index: int = 0):
    settings = load_settings()
    sample = load_samples()[sample_index]
    db = tmp_path / "hist.sqlite"
    client = SerpClient("", db, max_searches=20)
    preload_client(client, sample)
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
    return report, db, client


def test_run_is_persisted(tmp_path: Path):
    report, db, _client = _run(tmp_path)
    hist = RunHistory(db)
    run_id = hist.save(report)
    rows = hist.list_recent(15)
    assert run_id >= 1
    assert hist.count() == 1
    assert rows[0].novelty_score == report.novelty.score
    assert rows[0].radar_label == report.radar.label
    assert report.abstract[:20] in rows[0].abstract_text
    saved = SavedReport.from_compass(report)
    assert '"novelty"' in saved.model_dump_json()


def test_reload_matches_without_network(tmp_path: Path, monkeypatch):
    report, db, client = _run(tmp_path)
    hist = RunHistory(db)
    run_id = hist.save(report)
    used_before = client.meter.used_this_run

    def boom(*_a, **_k):
        raise AssertionError("network or LLM was called")

    monkeypatch.setattr("requests.get", boom)
    monkeypatch.setattr("core.llm.complete_json", boom)
    monkeypatch.setattr("core.qa.complete_json", boom)
    loaded = hist.load(run_id)
    assert loaded.novelty.score == report.novelty.score
    assert loaded.debate.verdict == report.debate.verdict
    assert loaded.radar.label == report.radar.label
    assert [i.id for i in loaded.store.all()] == [i.id for i in report.store.all()]
    assert [i.title for i in loaded.store.all()] == [i.title for i in report.store.all()]
    assert client.meter.used_this_run == used_before


def test_clear_history_leaves_cache(tmp_path: Path):
    report, db, client = _run(tmp_path)
    hist = RunHistory(db)
    hist.save(report)
    cache = SearchCache(db)
    cached = cache.total_entries()
    assert cached >= 1
    assert hist.count() == 1
    hist.clear()
    assert hist.count() == 0
    assert cache.total_entries() == cached
    assert client.cache.total_entries() == cached


def test_relative_time_hours():
    assert "hour" in relative_time(0, now=2 * 3600)


def test_bibtex_fields_come_from_store_only():
    item = EvidenceItem(
        id="SRC-001",
        run_id="r",
        engine="google_scholar",
        source_type="paper",
        quality="peer_reviewed",
        title="Graph neural downscaling",
        snippet="A GNN maps rainfall.",
        url="https://publisher.org/papers/gnn-downscaling",
        year=2022,
        authors=["L. Chen", "R. Mehta"],
        venue="Environmental Data Science 2022",
        cited_by=86,
        query="q",
    )
    blob = bibtex_entry(item)
    assert "@article" in blob
    assert "Graph neural downscaling" in blob
    assert "L. Chen" in blob
    assert "2022" in blob
    assert "https://publisher.org/papers/gnn-downscaling" in blob
    missing = EvidenceItem(
        id="SRC-002",
        run_id="r",
        engine="google",
        source_type="web",
        quality="web",
        title="Some page",
        snippet="",
        url="",
        year=None,
        authors=[],
        venue="",
        query="q",
    )
    sparse = bibtex_entry(missing)
    assert UNKNOWN["author"] in sparse
    assert UNKNOWN["year"] in sparse
    assert UNKNOWN["venue"] in sparse
    assert "2024" not in sparse
    assert "Invented Author" not in sparse
    bundle = bibtex_for_closest([item, missing])
    assert "@article" in bundle and "@misc" in bundle

    allowed = {
        item.title,
        " and ".join(item.authors),
        str(item.year),
        item.venue,
        item.url,
        f"cited_by {item.cited_by}",
        missing.title,
        *UNKNOWN.values(),
    }
    for raw in re.findall(r"=\s*\{([^{}]*)\}", blob):
        assert raw in allowed, f"untraceable BibTeX field: {raw}"
