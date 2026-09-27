"""Research Compass — Streamlit UI."""

from __future__ import annotations

import html as html_lib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.bibtex import bibtex_for_closest
from core.citations import safe_url
from core.source import public_link_label, source_by_id, source_from_evidence
from core.config import load_settings
from core.demo import exact_sample, load_samples, plan_from_fixtures, preload_client
from core.export import report_to_json, report_to_markdown, report_to_pdf
from core.history import HistoryRow, RunHistory, relative_time
from core.pipeline import CompassReport, run_compass
from core.qa import QAAnswer, answer_question
from core.serp import SerpClient
from core.store import EvidenceStore
from core.theme import (
    chat_bubble,
    current_theme,
    hero,
    inject_theme,
    plotly_layout,
    rating_pill,
    report_sphere,
    score_ring,
    source_link,
    stance_pill,
    summary_cards,
    theme_colors,
    type_tag,
    unavailable_note,
)
from modules.contradictions import QUALITY_WEIGHT

st.set_page_config(page_title="Research Compass", layout="wide", page_icon="🧭")


def _ensure_session() -> None:
    if "rc_theme_choice" not in st.session_state:
        prior = st.session_state.get("rc_theme")
        st.session_state.rc_theme_choice = "Dark" if prior == "dark" else "Light"
    if "qa_history" not in st.session_state:
        st.session_state.qa_history = []
    if "clear_hist_armed" not in st.session_state:
        st.session_state.clear_hist_armed = False
    if "abstract_text" not in st.session_state:
        st.session_state.abstract_text = ""
    st.session_state.rc_theme = "dark" if st.session_state.rc_theme_choice == "Dark" else "light"


_ensure_session()
inject_theme(current_theme())


def _history_db(settings) -> Path:
    return settings.cache_path


def _client(settings) -> SerpClient:
    return SerpClient(
        api_key=settings.serpapi_api_key,
        cache_path=settings.cache_path,
        max_searches=settings.max_searches_per_run,
        timeout=settings.serpapi_timeout,
        endpoint=settings.serpapi_endpoint,
    )


def source_chips(store, ids: list[str]) -> str:
    bits = []
    for sid in ids:
        if not sid:
            continue
        source = source_by_id(store, sid)
        bits.append(source_link(sid, source.url if source else None))
    return "".join(bits)


def render_sources(store, ids: list[str]) -> None:
    if not ids:
        st.caption("No sources cited in this section.")
        return
    st.markdown("Sources: " + source_chips(store, ids), unsafe_allow_html=True)


def _verdict_tone(debate) -> str:
    text = (debate.verdict or "").lower()
    if debate.advocate_score > debate.skeptic_score or (
        "pursue" in text and "do not" not in text and "don't" not in text
    ):
        return "good"
    if debate.skeptic_score > debate.advocate_score or "do not" in text or "don't" in text:
        return "bad"
    return "neutral"


def map_kind(source_type: str | None) -> str:
    t = (source_type or "").lower()
    return {
        "trends": "trend",
        "reimplementation": "github",
        "paper": "paper",
        "github": "github",
        "dataset": "dataset",
        "news": "news",
        "venue": "venue",
        "author": "author",
        "web": "web",
    }.get(t, t or "other")


def _title_link(title: str, url: str | None) -> str:
    t = html_lib.escape(title or "")
    href = safe_url(url)
    if href:
        return f'<a href="{html_lib.escape(href, quote=True)}" target="_blank" rel="noopener">{t}</a>'
    return t


def _clip(text: str, n: int = 140) -> str:
    t = " ".join((text or "").split())
    return t if len(t) <= n else t[: n - 1] + "…"


def _history_label(row: HistoryRow) -> str:
    return (
        f"{_clip(row.abstract_text, 52)}\n"
        f"Novelty: {row.novelty_score} · {row.verdict_label} · {relative_time(row.created_at)}"
    )


def progress_label(frac: float) -> str:
    if frac < 0.12:
        return "Preparing research query…"
    if frac < 0.55:
        return "Searching relevant literature…"
    if frac < 0.68:
        return "Organizing evidence…"
    if frac < 0.82:
        return "Evaluating supporting and contradicting sources…"
    if frac < 0.96:
        return "Building research report…"
    return "Finalizing insights…"


def render_history_sidebar(settings) -> None:
    st.subheader("Research History")
    hist = RunHistory(_history_db(settings))
    rows = hist.list_recent(15)
    if not rows:
        st.caption("No saved reports yet.")
    else:
        for row in rows:
            if st.button(_history_label(row), key=f"hist_{row.id}", use_container_width=True):
                st.session_state.report = hist.load(row.id)
                st.session_state.qa_history = []
                st.session_state.abstract_text = st.session_state.report.abstract
    if st.session_state.get("clear_hist_armed"):
        st.warning("Clear all saved research reports?")
        c1, c2 = st.columns(2)
        if c1.button("Confirm", key="clear_hist_yes"):
            hist.clear()
            st.session_state.clear_hist_armed = False
        if c2.button("Cancel", key="clear_hist_no"):
            st.session_state.clear_hist_armed = False
    elif st.button("Clear History", key="clear_hist"):
        st.session_state.clear_hist_armed = True


def weight_chart(report: CompassReport) -> None:
    colors = theme_colors()
    sw = sum(x.weight for x in report.contradictions.supporting)
    cw = sum(x.weight for x in report.contradictions.contradicting)
    fig = go.Figure(
        data=[
            go.Bar(
                y=["Supporting weight", "Contradicting weight"],
                x=[sw, cw],
                orientation="h",
                marker_color=[colors["sage"], colors["coral"]],
                hovertemplate="%{y}: %{x:.1f}<extra></extra>",
            )
        ]
    )
    layout = plotly_layout()
    layout["height"] = 170
    layout["showlegend"] = False
    layout["margin"] = dict(l=10, r=10, t=8, b=8)
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Peer-reviewed research is weighted more strongly than general web sources "
        f"(peer-reviewed {QUALITY_WEIGHT['peer_reviewed']}, repository {QUALITY_WEIGHT['repo']}, "
        f"news {QUALITY_WEIGHT['news']}, web {QUALITY_WEIGHT['web']}, blog {QUALITY_WEIGHT['blog']})."
    )


def connections_chart(report: CompassReport) -> None:
    colors = theme_colors()
    labels = ["This research"]
    xs, ys = [0.0], [0.0]
    for i, w in enumerate(report.novelty.closest_works[:6]):
        labels.append(_clip(w.title, 36))
        xs.append(1.15)
        ys.append(1.2 - i * 0.45)
    evid = report.store.all()[:8]
    for j, item in enumerate(evid):
        labels.append(item.id)
        xs.append(-1.15)
        ys.append(1.0 - j * 0.32)
    fig = go.Figure()
    for i in range(1, len(report.novelty.closest_works[:6]) + 1):
        fig.add_trace(
            go.Scatter(
                x=[0, xs[i]],
                y=[0, ys[i]],
                mode="lines",
                line=dict(color=colors["brass"], width=1),
                hoverinfo="skip",
                showlegend=False,
            )
        )
    n_close = len(report.novelty.closest_works[:6])
    for j in range(n_close + 1, len(labels)):
        fig.add_trace(
            go.Scatter(
                x=[0, xs[j]],
                y=[0, ys[j]],
                mode="lines",
                line=dict(color=colors["line"], width=1),
                hoverinfo="skip",
                showlegend=False,
            )
        )
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers+text",
            text=labels,
            textposition="top center",
            marker=dict(size=[18] + [11] * (len(labels) - 1), color=[colors["brass"]] + [colors["sage"]] * n_close + [colors["muted"]] * (len(labels) - 1 - n_close)),
            hovertext=labels,
            showlegend=False,
        )
    )
    layout = plotly_layout()
    layout["height"] = 320
    layout["xaxis"] = dict(visible=False)
    layout["yaxis"] = dict(visible=False)
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Research connections in this report: the current abstract, closest works, and cited evidence IDs. "
        "This is not a complete citation network."
    )


def render_compare(settings) -> None:
    hist = RunHistory(_history_db(settings))
    rows = hist.list_recent(15)
    if len(rows) < 2:
        st.caption("Save at least two reports to compare them.")
        return
    labels = {f"{r.id}: {_clip(r.abstract_text, 40)} (novelty {r.novelty_score})": r.id for r in rows}
    keys = list(labels)
    c1, c2 = st.columns(2)
    a = c1.selectbox("Report A", keys, key="cmp_a")
    b = c2.selectbox("Report B", keys, index=min(1, len(keys) - 1), key="cmp_b")
    if labels[a] == labels[b]:
        st.caption("Choose two different reports.")
        return
    ra, rb = hist.load(labels[a]), hist.load(labels[b])
    left, right = st.columns(2)
    for col, rep in ((left, ra), (right, rb)):
        with col:
            st.markdown(f"**Novelty {rep.novelty.score}** · {rep.radar.label}")
            st.write(_clip(rep.debate.verdict, 280))
            st.caption("Closest works")
            for w in rep.novelty.closest_works[:4]:
                st.write(f"- {w.title}")
            st.caption(
                f"Supporting {len(rep.contradictions.supporting)} · "
                f"Contradicting {len(rep.contradictions.contradicting)} · "
                f"Reproducibility {rep.reproducibility.rating}"
            )
            venues = ", ".join(v.name for v in rep.venues.rows[:4]) or "None listed"
            st.caption("Venues: " + venues)
    st.caption("Comparison is descriptive. It does not rank a winner.")


def render_report(report: CompassReport, settings) -> None:
    store = report.store
    n, d, r = report.novelty, report.debate, report.radar
    summary_cards(
        [
            {
                "label": "Novelty",
                "value": f"{n.score} / 100",
                "note": _clip(n.summary),
                "tone": "brass",
            },
            {
                "label": "Conclusion",
                "value": "Pursue" if _verdict_tone(d) == "good" else ("Hold" if _verdict_tone(d) == "bad" else "Split"),
                "note": _clip(d.verdict),
                "tone": _verdict_tone(d),
            },
            {
                "label": "Research radar",
                "value": r.label,
                "note": _clip(r.reasoning),
                "tone": "neutral",
            },
        ]
    )
    if n.thin_evidence or d.thin_evidence:
        st.warning("Evidence in this report is limited. Treat scores as weakly supported.")

    md = report_to_markdown(report, qa_turns=st.session_state.get("qa_history") or [])
    js = report_to_json(report)
    e1, e2, e3 = st.columns(3)
    e1.download_button("Download Research Report (.md)", md, file_name="research_compass_report.md", mime="text/markdown")
    e2.download_button("Download JSON", js, file_name="research_compass_report.json", mime="application/json")
    try:
        pdf = report_to_pdf(report, qa_turns=st.session_state.get("qa_history") or [])
        e3.download_button("Download PDF", pdf, file_name="research_compass_report.pdf", mime="application/pdf")
    except Exception:
        e3.caption("PDF export is unavailable in this environment.")

    tabs = st.tabs(
        [
            "Novelty",
            "Evidence",
            "Debate",
            "Reproducibility",
            "Research Radar",
            "Experts",
            "Venues",
            "Sources",
            "AI Research Assistant",
        ]
    )
    with tabs[0]:
        ring_col, list_col = st.columns([0.38, 1], vertical_alignment="top")
        with ring_col:
            score_ring(n.score)
            st.caption(_clip(n.summary, 220))
        with list_col:
            st.write(n.summary)
            render_sources(store, n.source_ids)
            for w in n.closest_works:
                source = source_by_id(store, w.source_id)
                href = source.url if source else None
                title = source.title if source else w.title
                title_html = _title_link(title, href)
                status = public_link_label(source) if source else "Link unavailable"
                extra = f' <span class="rc-unavail">{html_lib.escape(status)}</span>'
                st.markdown(
                    f"{source_link(w.source_id, href)} **{title_html}**{extra}",
                    unsafe_allow_html=True,
                )
                st.write(w.similarity_reason)
                if w.overlap_notes:
                    st.caption(w.overlap_notes)
            st.subheader("Research gap")
            for x in n.differentiation:
                st.write(f"- {x}")
            with st.expander("Copy as BibTeX"):
                items = [store.by_id(w.source_id) for w in n.closest_works]
                items = [i for i in items if i]
                if not items:
                    st.caption("No closest-work metadata in this report.")
                else:
                    st.code(bibtex_for_closest(items), language="bibtex")
        st.subheader("Research connections")
        connections_chart(report)

    with tabs[1]:
        st.write(report.contradictions.balance_note)
        st.markdown(f"**Core claim (from abstract):** {report.contradictions.core_claim}")
        weight_chart(report)
        left, right = st.columns(2)
        with left:
            st.markdown('<div class="rc-ev-col sage"><h3>Supporting evidence</h3>', unsafe_allow_html=True)
            if not report.contradictions.supporting:
                st.caption("None in this report.")
            for row in report.contradictions.supporting:
                source = source_by_id(store, row.source_id)
                kind = map_kind(source.source_type if source else "")
                href = source.url if source else None
                title = source.title if source else row.title
                st.markdown(
                    f'<div class="rc-ev-item">{type_tag(kind)} {_title_link(title, href)} '
                    f"{stance_pill(row.stance)} {source_link(row.source_id, href)}<br>"
                    f"{html_lib.escape(row.why)}</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)
        with right:
            st.markdown('<div class="rc-ev-col coral"><h3>Contradicting evidence</h3>', unsafe_allow_html=True)
            if not report.contradictions.contradicting:
                st.caption("None in this report.")
            for row in report.contradictions.contradicting:
                source = source_by_id(store, row.source_id)
                kind = map_kind(source.source_type if source else "")
                href = source.url if source else None
                title = source.title if source else row.title
                st.markdown(
                    f'<div class="rc-ev-item">{type_tag(kind)} {_title_link(title, href)} '
                    f"{stance_pill(row.stance)} {source_link(row.source_id, href)}<br>"
                    f"{html_lib.escape(row.why)}</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)
        n_neutral = len(report.contradictions.neutral)
        with st.expander(f"Neutral / context ({n_neutral})"):
            if not report.contradictions.neutral:
                st.caption("None in this report.")
            for row in report.contradictions.neutral:
                source = source_by_id(store, row.source_id)
                kind = map_kind(source.source_type if source else "")
                href = source.url if source else None
                title = source.title if source else row.title
                st.markdown(
                    f'<div class="rc-ev-item">{type_tag(kind)} {_title_link(title, href)} '
                    f"{stance_pill('neutral')} {source_link(row.source_id, href)}<br>"
                    f"{html_lib.escape(row.why)}</div>",
                    unsafe_allow_html=True,
                )
        st.subheader("Why conclusions differ")
        for dis in report.contradictions.disagreements:
            st.markdown(f"**{dis.theme}.** {dis.explanation}")
            render_sources(store, dis.source_ids)

    with tabs[2]:
        render_sources(store, d.source_ids)
        for turn in d.transcript:
            chips = source_chips(store, turn.source_ids)
            chat_bubble(turn.speaker, turn.text, chips)

    with tabs[3]:
        rp = report.reproducibility
        st.markdown(f'<div class="rc-rating-wrap">{rating_pill(rp.rating)}</div>', unsafe_allow_html=True)
        st.write(rp.summary)
        render_sources(store, rp.source_ids)
        for a in rp.artifacts:
            source = source_by_id(store, a.source_id)
            href = source.url if source else None
            title = source.title if source else a.title
            st.markdown(
                f'<div class="rc-repro-item">{type_tag(a.kind)} {_title_link(title, href)} '
                f"{source_link(a.source_id, href)}<br>"
                f"{html_lib.escape(a.what_it_offers)}</div>",
                unsafe_allow_html=True,
            )
            if a.missing:
                st.caption("Not found in this report: " + a.missing)
        if rp.missing:
            st.subheader("Unavailable evidence")
            for m in rp.missing:
                st.write(f"- {m}")

    with tabs[4]:
        st.write(f"**{r.label}.** {r.reasoning}")
        render_sources(store, r.source_ids)
        left, right = st.columns(2)
        layout = plotly_layout()
        if r.scholar_by_year:
            df = pd.DataFrame([y.model_dump() for y in r.scholar_by_year])
            fig = go.Figure(go.Bar(x=df["year"], y=df["papers"], marker_color=theme_colors()["brass"]))
            fig.update_layout(**layout, title="Publication years in this report")
            left.plotly_chart(fig, use_container_width=True)
        else:
            left.caption("No year histogram in this report.")
        if r.trend_points:
            df = pd.DataFrame([p.model_dump() for p in r.trend_points])
            fig = go.Figure(go.Scatter(x=df["date"], y=df["value"], mode="lines", line=dict(color=theme_colors()["sage"])))
            fig.update_layout(**layout, title="Interest over time in this report")
            right.plotly_chart(fig, use_container_width=True)
        else:
            right.caption("No interest timeline in this report.")
        st.caption(f"News items in this report: {r.news_count}")
        report_sphere(
            n.score,
            len(store.all()),
            sum(1 for i in store.all() if (i.cited_by or 0) > 0 or i.source_type == "paper"),
        )

    with tabs[5]:
        ex = report.experts
        render_sources(store, ex.source_ids)
        for e in ex.who_to_read_first:
            st.markdown(
                f"{type_tag('author')} **{html_lib.escape(e.name)}**"
                + (f" — {html_lib.escape(e.affiliation)}" if e.affiliation else ""),
                unsafe_allow_html=True,
            )
            st.write(e.why_read)
            render_sources(store, e.source_ids)
        if ex.labs:
            st.caption("Affiliations mentioned in this report: " + "; ".join(ex.labs))
        st.subheader("Draft introduction")
        st.caption("This text is a draft only. No researcher has been contacted.")
        st.code(ex.intro_email or "Not enough author evidence in this report.", language="text")

    with tabs[6]:
        vn = report.venues
        st.write(vn.summary)
        render_sources(store, vn.source_ids)
        if vn.rows:
            for row in vn.rows:
                india = (
                    '<span class="rc-pill sage">India-relevant</span>'
                    if row.india_relevant
                    else '<span class="rc-pill muted">Global</span>'
                )
                deadline = row.deadline if row.deadline and row.deadline != "not found" else None
                dl = (
                    html_lib.escape(deadline)
                    if deadline
                    else '<span class="rc-deadline-missing">Not found in source text</span>'
                )
                kind = "venue" if row.kind in {"conference", "workshop", "grant", "fellowship", "other", "venue"} else row.kind
                source = source_by_id(store, row.source_id)
                href = source.url if source else None
                st.markdown(
                    f'<div class="rc-venue-card"><strong>{html_lib.escape(row.name)}</strong> {type_tag(kind)} {india}<br>'
                    f"Deadline: {dl}<br>"
                    f"{source_link(row.source_id, href)}</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No venue or grant-like sources in this report.")

    with tabs[7]:
        items = store.all()
        if not items:
            st.caption("No sources in this report.")
        else:
            for i in items:
                source = source_from_evidence(i)
                href = source.url
                authors = ", ".join(source.authors) if source.authors else "—"
                year = source.year or "—"
                venue = source.venue or "—"
                link_html = (
                    f'<a href="{html_lib.escape(href, quote=True)}" target="_blank" rel="noopener">{html_lib.escape(href)}</a>'
                    if href
                    else unavailable_note()
                )
                st.markdown(
                    f'<div class="rc-source-card">{source_link(source.source_id, href)} {type_tag(map_kind(source.source_type))}<br>'
                    f"<strong>{_title_link(source.title, href)}</strong> "
                    f'<span class="rc-unavail">{html_lib.escape(public_link_label(source))}</span><br>'
                    f"{html_lib.escape(authors)} · {html_lib.escape(str(year))} · {html_lib.escape(str(venue))}<br>"
                    f"{link_html}</div>",
                    unsafe_allow_html=True,
                )

    with tabs[8]:
        st.subheader("AI Research Assistant")
        st.write(
            "Ask questions about the research report and get answers grounded in the evidence "
            "collected for this analysis."
        )
        examples = [
            "What is the main research gap?",
            "Which sources contradict this paper?",
            "What makes this research novel?",
            "Which related work is closest to this study?",
            "What are the main reproducibility concerns?",
            "Summarize the strongest evidence.",
        ]
        st.caption("Example prompts")
        cols = st.columns(2)
        for i, q in enumerate(examples):
            if cols[i % 2].button(q, key=f"qa_ex_{i}", use_container_width=True):
                st.session_state.qa_pending = q
        pending = st.session_state.pop("qa_pending", None)
        history: list[dict] = list(st.session_state.get("qa_history") or [])
        if pending:
            with st.spinner("Reading this report’s evidence…"):
                ans: QAAnswer = answer_question(
                    pending,
                    report,
                    settings=settings,
                    use_llm=bool(settings.has_llm) and report.mode == "live",
                )
            valid = [sid for sid in ans.cited_source_ids if store.by_id(sid)]
            history.append({"q": pending, "a": ans.answer, "ids": valid})
            st.session_state.qa_history = history
        if not history:
            st.info("No questions yet. Try an example prompt, or type your own below.")
        for turn in history:
            with st.chat_message("user"):
                st.write(turn["q"])
            with st.chat_message("assistant"):
                st.write(turn["a"])
                chips = source_chips(store, turn.get("ids") or [])
                if chips:
                    st.markdown(chips, unsafe_allow_html=True)
        prompt = st.chat_input("Ask about this report’s evidence")
        if prompt:
            with st.spinner("Reading this report’s evidence…"):
                ans = answer_question(
                    prompt,
                    report,
                    settings=settings,
                    use_llm=bool(settings.has_llm) and report.mode == "live",
                )
            valid = [sid for sid in ans.cited_source_ids if store.by_id(sid)]
            history.append({"q": prompt, "a": ans.answer, "ids": valid})
            st.session_state.qa_history = history
            st.rerun()


def main() -> None:
    settings = load_settings()
    samples = load_samples()

    with st.sidebar:
        st.subheader("Appearance")
        st.radio(
            "Theme",
            ["Light", "Dark"],
            key="rc_theme_choice",
            horizontal=True,
            label_visibility="collapsed",
        )

        if not settings.has_serpapi:
            st.info("Research search is currently unavailable. Please configure the required API credentials.")

        st.subheader("Example abstracts")
        names = ["(none)"] + [f"{s.title}" for s in samples]
        choice = st.selectbox("Load an example", names)
        if choice != "(none)":
            picked = next(s for s in samples if s.title == choice)
            if st.button("Load example into editor"):
                st.session_state.abstract_text = picked.abstract
        render_history_sidebar(settings)
        st.subheader("Compare research")
        render_compare(settings)

    hero()

    abstract = st.text_area(
        "Research abstract",
        key="abstract_text",
        height=180,
        placeholder="Paste your research abstract here…",
    )
    st.markdown(f'<div class="rc-count">{len(abstract or "")} characters</div>', unsafe_allow_html=True)
    run = st.button("Analyze Research", type="primary")

    if run:
        if not (abstract or "").strip():
            st.error("Paste a research abstract to continue.")
            return
        sample = exact_sample(abstract, samples)
        if not settings.has_serpapi and sample is None:
            st.error("Research search is currently unavailable. Please configure the required API credentials.")
            return
        progress = st.progress(0.0, text="Preparing research query…")

        def on_progress(_msg: str, frac: float) -> None:
            progress.progress(min(1.0, max(0.0, frac)), text=progress_label(frac))

        mode = "live" if settings.has_serpapi else "demo"
        preset = None
        client = _client(settings)
        if mode == "demo" and sample is not None:
            preload_client(client, sample)
            preset = plan_from_fixtures(sample)
        store = EvidenceStore()
        try:
            report = run_compass(
                abstract.strip(),
                mode=mode,
                client=client,
                store=store,
                settings=settings,
                sample_id=sample.id if sample else None,
                use_llm=(mode == "live" and settings.has_llm),
                preset_plan=preset,
                progress=on_progress,
            )
        except Exception:
            st.error("We couldn't complete this research analysis. Please try again.")
            return
        RunHistory(_history_db(settings)).save(report)
        st.session_state.report = report
        st.session_state.qa_history = []
        progress.progress(1.0, text="Finalizing insights…")
        st.rerun()

    if "report" in st.session_state:
        render_report(st.session_state.report, settings)


if __name__ == "__main__":
    main()
