from pathlib import Path

from core.citations import UNAVAILABLE, is_http_url, is_valid_source_url, safe_url, unique_ids, url_title_pairs_are_consistent
from core.config import load_settings
from core.demo import load_samples, plan_from_fixtures, preload_client
from core.export import report_to_markdown, report_to_pdf
from core.pipeline import run_compass
from core.serp import SerpClient
from core.source import source_by_id, source_from_evidence, sources_from_store
from core.store import EvidenceItem, EvidenceStore
from core.theme import source_link, unavailable_note


def _item(**kwargs) -> EvidenceItem:
    base = dict(
        id="SRC-001",
        run_id="r",
        engine="google_scholar",
        source_type="paper",
        quality="peer_reviewed",
        title="Paper A",
        url="",
        authors=["A. Author"],
        venue="A Venue",
        year=2022,
        snippet="A snippet.",
    )
    base.update(kwargs)
    return EvidenceItem(**base)


def _report(tmp_path: Path):
    settings = load_settings()
    sample = load_samples()[0]
    client = SerpClient("", tmp_path / "src.sqlite", max_searches=20)
    preload_client(client, sample)
    return run_compass(
        sample.abstract,
        mode="demo",
        client=client,
        store=EvidenceStore(),
        settings=settings,
        sample_id=sample.id,
        use_llm=False,
        preset_plan=plan_from_fixtures(sample),
    )


def test_unrelated_sources_cannot_share_a_url():
    items = [
        _item(id="SRC-001", title="Paper A", url="https://publisher.org/a"),
        _item(id="SRC-002", title="Paper B", url="https://publisher.org/a"),
    ]
    assert not url_title_pairs_are_consistent(items)


def test_source_identity_fields_belong_to_one_record():
    item = _item(
        id="SRC-001",
        title="Graph neural downscaling",
        url="https://publisher.org/papers/gnn",
        authors=["L. Chen", "R. Mehta"],
        venue="Environmental Data Science",
        year=2022,
        snippet="A GNN maps rainfall.",
    )
    source = source_from_evidence(item)
    assert source.source_id == "SRC-001"
    assert source.title == item.title
    assert source.url == item.url
    assert source.authors == item.authors
    assert source.venue == item.venue
    assert source.year == item.year
    assert source.snippet == item.snippet


def test_rendered_link_equals_stored_url():
    item = _item(url="https://publisher.org/paper/123")
    html = source_link(item.id, source_from_evidence(item).url)
    assert "https://publisher.org/paper/123" in html
    assert html.count("href=") == 1


def test_source_id_does_not_generate_a_url():
    item = _item(id="SRC-009", url="https://arxiv.org/abs/SRC-009")
    assert source_from_evidence(item).url is None
    assert source_from_evidence(item).link_status == "invalid"
    item2 = _item(id="SRC-009", url="")
    assert source_from_evidence(item2).url is None
    html = source_link("SRC-009", source_from_evidence(item2).url)
    assert "href=" not in html
    assert "arxiv.org" not in html


def test_missing_url_renders_plain_text():
    html = source_link("SRC-001", source_from_evidence(_item(url="")).url)
    assert "href=" not in html
    assert "<a" not in html
    note = unavailable_note()
    assert UNAVAILABLE in note
    assert "href=" not in note


def test_placeholder_urls_are_rejected():
    assert is_valid_source_url("https://publisher.org/s41612-024-example") is False
    assert is_valid_source_url("http://localhost/paper") is False
    assert is_valid_source_url("https://demo.research-compass.local/a") is False
    assert source_from_evidence(_item(url="https://publisher.org/fake-paper")).url is None
    assert safe_url("https://trends.google.com/") is None
    assert is_valid_source_url("https://publisher.org/papers/gnn") is True


def test_fixture_sources_do_not_point_at_unrelated_real_papers(tmp_path: Path):
    for sample in load_samples():
        blob = (Path("demo_data") / sample.fixture_file).read_text(encoding="utf-8").lower()
        assert "arxiv.org" not in blob
        assert "doi.org" not in blob
        assert "https://" not in blob
    report = _report(tmp_path)
    for source in sources_from_store(report.store):
        assert source.url is None
        assert source.link_status == "unavailable"


def test_rendering_does_not_modify_stored_url():
    item = _item(url="https://publisher.org/paper/123")
    original = item.url
    source_link(item.id, source_from_evidence(item).url)
    assert item.url == original


def test_ingested_ids_unique_and_urls_consistent(tmp_path: Path):
    report = _report(tmp_path)
    items = report.store.all()
    assert unique_ids(items)
    assert url_title_pairs_are_consistent(items)
    for item in items:
        source = source_from_evidence(item)
        assert source.title == item.title
        assert source.authors == item.authors
        assert source.year == item.year
        assert source.venue == item.venue
        if source.url:
            assert source.url == item.url.strip()


def test_closest_work_urls_match_store(tmp_path: Path):
    report = _report(tmp_path)
    for w in report.novelty.closest_works:
        item = report.store.by_id(w.source_id)
        source = source_by_id(report.store, w.source_id)
        assert item is not None and source is not None
        assert w.title == item.title == source.title
        assert source.url is None or source.url == item.url


def test_downloads_match_canonical_sources(tmp_path: Path):
    report = _report(tmp_path)
    md = report_to_markdown(report, qa_turns=[{"q": "What is the gap?", "a": "See the report.", "ids": ["SRC-001"]}])
    pdf = report_to_pdf(report)
    assert "## Sources" in md
    assert "| ID | Title | Type | Year | Venue | Link |" in md
    assert "Not available" in md
    assert "AI Research Assistant" in md
    assert "https://" not in md
    assert b"Source link unavailable" in pdf
    assert b"arxiv.org" not in pdf
    for source in sources_from_store(report.store):
        assert source.source_id in md
        assert source.title.split("|")[0][:40] in md or source.title[:20] in md
        assert source.url is None


def test_source_link_never_clickable_for_unverified_url():
    html = source_link("SRC-001", "")
    assert "href=" not in html
    html = source_link("SRC-002", "javascript:alert(1)")
    assert "href=" not in html
    html = source_link("SRC-003", "https://publisher.org/s41612-example")
    assert "href=" not in html
    html = source_link("SRC-004", "https://publisher.org/paper")
    assert 'href="https://publisher.org/paper"' in html


def test_is_http_url_rejects_junk():
    assert not is_http_url("not-a-url")
    assert not is_http_url("javascript:void(0)")
    assert is_http_url("https://publisher.org/a")
    assert safe_url("https://trends.google.com/") is None
