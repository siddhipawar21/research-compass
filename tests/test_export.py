from pathlib import Path

from core.config import load_settings
from core.demo import load_samples, plan_from_fixtures, preload_client
from core.export import report_to_json, report_to_markdown, report_to_pdf
from core.pipeline import run_compass
from core.serp import SerpClient
from core.store import EvidenceStore


def _report(tmp_path: Path):
    settings = load_settings()
    sample = load_samples()[0]
    client = SerpClient("", tmp_path / "e.sqlite", max_searches=20)
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


def test_markdown_export_has_required_sections(tmp_path: Path):
    md = report_to_markdown(_report(tmp_path))
    for heading in (
        "Executive summary",
        "Abstract",
        "Novelty",
        "Closest existing work",
        "Research gap",
        "Evidence",
        "Debate",
        "Reproducibility",
        "Research radar",
        "Experts",
        "Venues",
        "AI Research Assistant",
        "Sources",
    ):
        assert heading in md
    assert "SerpApi" not in md
    assert "API credits" not in md
    assert "250/month" not in md


def test_json_and_pdf_export(tmp_path: Path):
    report = _report(tmp_path)
    js = report_to_json(report)
    assert '"novelty"' in js
    assert '"evidence"' in js
    pdf = report_to_pdf(report)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 200
