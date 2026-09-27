"""User-facing report exports. URLs come only from canonical Source records."""

from __future__ import annotations

import io
import re

from core.history import SavedReport
from core.pipeline import CompassReport
from core.source import Source, public_link_label, source_by_id, sources_from_store


def _esc_cell(text: str) -> str:
    return (text or "").replace("|", "/").replace("\n", " ")


def _md_link(source: Source | None) -> str:
    if source and source.url:
        return f"[Open source]({source.url})"
    return "Not available"


def _src_md(report: CompassReport, ids: list[str]) -> str:
    bits = []
    for sid in ids:
        source = source_by_id(report.store, sid)
        if source and source.url:
            bits.append(f"[{source.source_id}]({source.url})")
        else:
            bits.append(sid)
    return ", ".join(bits) if bits else "_none_"


def _work_line(report: CompassReport, source_id: str, reason: str) -> str:
    source = source_by_id(report.store, source_id)
    if source is None:
        return f"- {source_id} — {reason}"
    title = source.title
    if source.url:
        head = f"[{title}]({source.url})"
    else:
        head = f"{title} (URL: Not available)"
    return f"- {head} — {reason} ({source.source_id})"


def report_to_markdown(report: CompassReport, qa_turns: list[dict] | None = None) -> str:
    n = report.novelty
    d = report.debate
    r = report.radar
    sources = sources_from_store(report.store)
    exec_sum = (
        f"Novelty is scored {n.score}/100. Overall conclusion: {d.verdict.strip()} "
        f"Research radar: {r.label}."
    )
    lines = [
        "# Research Compass report",
        "",
        "## Executive summary",
        "",
        exec_sum,
        "",
        f"**Novelty:** {n.score}/100  ",
        f"**Research radar:** {r.label}  ",
        f"**Conclusion:** {d.verdict}",
        "",
        "## Abstract",
        "",
        report.abstract.strip(),
        "",
        "## Novelty",
        "",
        n.summary,
        "",
        "## Closest existing work",
        "",
    ]
    if not n.closest_works:
        lines.append("_None in this report._")
        lines.append("")
    for w in n.closest_works:
        lines.append(_work_line(report, w.source_id, w.similarity_reason))
    lines += ["", "## Research gap", ""]
    for x in n.differentiation:
        lines.append(f"- {x}")
    if not n.differentiation:
        lines.append("_None stated._")
    c = report.contradictions
    lines += ["", "## Evidence", "", c.balance_note, "", f"**Claim:** {c.core_claim}", ""]
    for label, rows in (
        ("Supporting", c.supporting),
        ("Contradicting", c.contradicting),
        ("Neutral", c.neutral),
    ):
        lines += [f"### {label}", ""]
        if not rows:
            lines.append("_None in this report._")
            lines.append("")
            continue
        for row in rows:
            source = source_by_id(report.store, row.source_id)
            title = source.title if source else row.title
            link = _md_link(source)
            lines.append(f"- {title} ({row.source_id}) — {row.why} — {link}")
        lines.append("")
    lines += ["### Why conclusions differ", ""]
    for dis in c.disagreements:
        lines.append(f"- **{dis.theme}:** {dis.explanation} ({_src_md(report, dis.source_ids)})")
    lines += ["", "## Debate", ""]
    for turn in d.transcript:
        lines.append(f"**{turn.speaker}:** {turn.text}")
        lines.append(f"  Citations: {_src_md(report, turn.source_ids)}")
        lines.append("")
    rp = report.reproducibility
    lines += ["", "## Reproducibility", "", f"**Rating:** {rp.rating} — {rp.summary}", ""]
    for a in rp.artifacts:
        source = source_by_id(report.store, a.source_id)
        link = _md_link(source)
        title = source.title if source else a.title
        lines.append(f"- ({a.kind}) {title} ({a.source_id}) — {a.what_it_offers} — {link}")
        if a.missing:
            lines.append(f"  - Missing: {a.missing}")
    if rp.missing:
        lines += ["", "Unavailable evidence:"]
        for m in rp.missing:
            lines.append(f"- {m}")
    lines += ["", "## Research radar", "", f"**{r.label}** — {r.reasoning}", ""]
    if r.scholar_by_year:
        lines.append("Publication years in this report: " + ", ".join(f"{y.year}:{y.papers}" for y in r.scholar_by_year))
    lines.append(f"News items in this report: {r.news_count}")
    lines.append(f"Citations: {_src_md(report, r.source_ids)}")
    ex = report.experts
    lines += ["", "## Experts", ""]
    if not ex.who_to_read_first:
        lines.append("_No researchers identified in this report._")
    for e in ex.who_to_read_first:
        aff = f" ({e.affiliation})" if getattr(e, "affiliation", "") else ""
        lines.append(f"- **{e.name}**{aff} — {e.why_read} ({_src_md(report, e.source_ids)})")
    if ex.intro_email:
        lines += ["", "### Draft introduction (not sent)", "", "```", ex.intro_email, "```"]
    vn = report.venues
    lines += [
        "",
        "## Venues",
        "",
        vn.summary,
        "",
        "| Name | Kind | Region | Deadline | Source |",
        "|---|---|---|---|---|",
    ]
    for row in vn.rows:
        source = source_by_id(report.store, row.source_id)
        name = _esc_cell(row.name)
        src = _md_link(source) if source else "Not available"
        lines.append(
            f"| {name} | {row.kind} | {'India-relevant' if row.india_relevant else 'Global'} | {_esc_cell(row.deadline)} | {src} |"
        )
    lines += ["", "## AI Research Assistant", ""]
    if not qa_turns:
        lines.append("_No questions were asked about this report._")
        lines.append("")
    else:
        for turn in qa_turns:
            lines.append(f"**Q:** {turn.get('q', '')}")
            lines.append("")
            lines.append(turn.get("a", ""))
            ids = turn.get("ids") or []
            if ids:
                lines.append("")
                lines.append("Sources: " + _src_md(report, ids))
            lines.append("")
    lines += [
        "",
        "## Sources",
        "",
        "| ID | Title | Type | Year | Venue | Link |",
        "|---|---|---|---|---|---|",
    ]
    for source in sources:
        year = str(source.year) if source.year else "—"
        lines.append(
            "| {id} | {title} | {typ} | {year} | {venue} | {link} |".format(
                id=source.source_id,
                title=_esc_cell(source.title),
                typ=_esc_cell(source.source_type),
                year=year,
                venue=_esc_cell(source.venue) or "—",
                link=_md_link(source),
            )
        )
    lines += [
        "",
        "---",
        "Claims in this report are bound to source IDs collected for this abstract. "
        "A link is included only when that same source record has a verified URL. "
        "Deadlines that were not in snippets are marked `not found`.",
        "",
    ]
    return "\n".join(lines)


def report_to_json(report: CompassReport) -> str:
    return SavedReport.from_compass(report).model_dump_json(indent=2)


def _pdf_text(text: str) -> str:
    return (text or "").encode("latin-1", "replace").decode("latin-1")


def report_to_pdf(report: CompassReport, qa_turns: list[dict] | None = None) -> bytes:
    from fpdf import FPDF

    class ReportPDF(FPDF):
        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica", size=9)
            self.set_text_color(90, 100, 120)
            self.cell(0, 8, f"{self.page_no()}", align="C")

    pdf = ReportPDF()
    pdf.compress = False
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(16, 16, 16)
    pdf.add_page()
    n, d, r = report.novelty, report.debate, report.radar

    def h1(text: str) -> None:
        pdf.set_text_color(20, 24, 43)
        pdf.set_font("Helvetica", "B", 16)
        pdf.multi_cell(0, 8, _pdf_text(text))
        pdf.ln(1)

    def h2(text: str) -> None:
        pdf.ln(2)
        pdf.set_text_color(185, 130, 46)
        pdf.set_font("Helvetica", "B", 13)
        pdf.multi_cell(0, 7, _pdf_text(text))
        pdf.set_text_color(20, 24, 43)
        pdf.ln(1)

    def body(text: str) -> None:
        pdf.set_font("Helvetica", size=11)
        pdf.set_text_color(20, 24, 43)
        pdf.multi_cell(0, 6, _pdf_text(text))
        pdf.ln(1)

    h1("Research Compass")
    body("Grounded research intelligence report")
    h2("Executive summary")
    body(
        f"Novelty {n.score}/100. Conclusion: {d.verdict.strip()} Research radar: {r.label}."
    )
    h2("Abstract")
    body(report.abstract.strip())
    h2("Novelty")
    body(n.summary)
    h2("Closest existing work")
    if not n.closest_works:
        body("None in this report.")
    for w in n.closest_works:
        source = source_by_id(report.store, w.source_id)
        title = source.title if source else w.source_id
        body(f"{title} ({w.source_id})")
        body(w.similarity_reason)
        if source and source.url:
            pdf.set_text_color(20, 80, 140)
            pdf.set_font("Helvetica", size=10)
            pdf.multi_cell(0, 5, _pdf_text(source.url), link=source.url)
            pdf.ln(1)
        else:
            body("Source link unavailable")
    h2("Research gap")
    for x in n.differentiation or ["None stated."]:
        body(f"- {x}")
    h2("Evidence")
    body(report.contradictions.balance_note)
    body(f"Claim: {report.contradictions.core_claim}")
    for label, rows in (
        ("Supporting", report.contradictions.supporting),
        ("Contradicting", report.contradictions.contradicting),
        ("Neutral", report.contradictions.neutral),
    ):
        body(label)
        if not rows:
            body("None in this report.")
        for row in rows:
            source = source_by_id(report.store, row.source_id)
            title = source.title if source else row.title
            body(f"{title} ({row.source_id}) — {row.why}")
            if source and source.url:
                pdf.set_text_color(20, 80, 140)
                pdf.set_font("Helvetica", size=10)
                pdf.multi_cell(0, 5, _pdf_text(source.url), link=source.url)
            else:
                body("Source link unavailable")
    h2("Debate")
    for turn in d.transcript:
        body(f"{turn.speaker}: {turn.text}")
        body("Citations: " + ", ".join(turn.source_ids or []) or "none")
    h2("Reproducibility")
    body(f"Rating: {report.reproducibility.rating} — {report.reproducibility.summary}")
    for a in report.reproducibility.artifacts:
        source = source_by_id(report.store, a.source_id)
        body(f"{a.kind}: {source.title if source else a.title} ({a.source_id})")
        if source and source.url:
            pdf.set_text_color(20, 80, 140)
            pdf.set_font("Helvetica", size=10)
            pdf.multi_cell(0, 5, _pdf_text(source.url), link=source.url)
        else:
            body("Source link unavailable")
    h2("Research radar")
    body(f"{r.label}. {r.reasoning}")
    h2("Experts")
    if not report.experts.who_to_read_first:
        body("No researchers identified in this report.")
    for e in report.experts.who_to_read_first:
        body(f"{e.name} — {e.why_read}")
    if report.experts.intro_email:
        body("Draft introduction (not sent):")
        body(report.experts.intro_email)
    h2("Venues")
    body(report.venues.summary)
    for row in report.venues.rows:
        source = source_by_id(report.store, row.source_id)
        body(f"{row.name} ({row.kind}) — deadline {row.deadline}")
        if source and source.url:
            pdf.set_text_color(20, 80, 140)
            pdf.set_font("Helvetica", size=10)
            pdf.multi_cell(0, 5, _pdf_text(source.url), link=source.url)
        else:
            body("Source link unavailable")
    h2("AI Research Assistant")
    if not qa_turns:
        body("No questions were asked about this report.")
    else:
        for turn in qa_turns:
            body(f"Q: {turn.get('q', '')}")
            body(turn.get("a", ""))
    h2("Source appendix")
    for source in sources_from_store(report.store):
        body(source.source_id)
        body(f"Title: {source.title}")
        body(f"Type: {source.source_type}")
        authors = ", ".join(source.authors) if source.authors else "—"
        body(f"Authors: {authors}")
        body(f"Venue: {source.venue or '—'}")
        body(f"Year: {source.year or '—'}")
        body("Source:")
        if source.url:
            pdf.set_text_color(20, 80, 140)
            pdf.set_font("Helvetica", size=10)
            pdf.multi_cell(0, 5, _pdf_text(source.url), link=source.url)
            pdf.ln(1)
        else:
            body("Source link unavailable")
        body(public_link_label(source))
    out = pdf.output()
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    buf = io.BytesIO()
    buf.write(out.encode("latin-1", "replace") if isinstance(out, str) else out)
    return buf.getvalue()
