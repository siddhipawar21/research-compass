# Research Compass

Research Compass turns a research abstract into a **grounded research intelligence report**: novelty, supporting and contradicting evidence, a sourced debate, reproducibility, topic radar, experts, venues, and a Q&A assistant that may only use the current report.

It is a local Streamlit application. Literature results come from configured search credentials (not from a model’s prior knowledge). Every claim is tied to a source ID (`SRC-001` …). If evidence is thin, the report says so. Deadlines that are not in a snippet are marked **not found**, never invented.

## Problem it solves

Literature review for a new idea is slow, and chat models will invent papers. Researchers need a dossier they can audit: what already exists, where the evidence conflicts, and what to do next — with links that belong to the sources they cite.

## Core insight

The useful unit of work is a **search-backed report**. The model (when used) may only reason over retrieved items. Unknown source IDs are dropped. Titles and URLs stay paired to the same evidence record.

## Feature overview

- Paste an abstract and run **Analyze Research**
- Report tabs: Novelty, Evidence, Debate, Reproducibility, Radar, Experts, Venues, Sources, Q&A
- Evidence weights visualized from the existing quality-weighting rule (peer-reviewed sources count more than news or blogs)
- BibTeX export for closest works using only stored metadata
- Persistent **Research History** in the same SQLite file as the search cache
- Reload a past report without repeating searches
- Compare two saved reports side by side (descriptive, not a ranking)
- Research connections diagram (this report’s closest works and cited IDs — not a full citation network)
- Export Markdown, JSON, and PDF
- Light theme by default, optional dark theme

## Architecture

```text
Abstract
  → query planner (8–12 engine-tagged searches)
  → search client (SQLite cache, per-run cap, retries)
  → evidence store (normalized SRC-xxx items)
  → seven analysis modules + grounded Q&A
  → Streamlit report + history + export
```

Live analysis optionally sends **store contents** to a language model via `core/llm.py`. The model may not add papers, URLs, authors, or dates.

## Setup

Requires **Python 3.11+**.

```bash
git clone <this-repo>
cd <this-repo>
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Environment variables

Set these in `.env` locally, or in the host’s secret manager when deploying. Never commit real keys.

| Variable | Required | Purpose |
| --- | --- | --- |
| `SERPAPI_API_KEY` | Yes for live search | Literature search |
| `ANTHROPIC_API_KEY` | No | Optional analysis of retrieved evidence |
| `ANTHROPIC_MODEL` | No | Default is listed in `.env.example` |
| `MAX_SEARCHES_PER_RUN` | No | Per-run search cap (default 20) |
| `CACHE_PATH` | No | SQLite cache + history (default `data/cache.sqlite`) |
| `SERPAPI_TIMEOUT_SECONDS` | No | Request timeout |
| `LLM_MAX_RETRIES` | No | JSON-retry budget for analysis |

`.env` is gitignored. `.env.example` contains placeholders only.

## Running locally

```bash
streamlit run app.py
```

Paste an abstract and click **Analyze Research**. Example abstracts in the sidebar load text only; with search credentials configured, analysis uses live retrieval. Without credentials, an exact example abstract can still produce a report from bundled search-shaped fixtures so the product can be reviewed offline. Custom abstracts require credentials.

## Deployment (Streamlit Community Cloud)

1. Push this repository to GitHub.
2. Create an app at [share.streamlit.io](https://share.streamlit.io) pointing at `app.py`.
3. In the app’s **Secrets**, add:

```toml
SERPAPI_API_KEY = "your-key"
ANTHROPIC_API_KEY = "optional-key"
```

Streamlit Cloud injects secrets as environment variables. Do not put keys in the repo or in the UI.

## Research workflow

1. Open Research Compass (light theme by default).
2. Paste an abstract (or load an example).
3. Click **Analyze Research**.
4. Read Novelty → Evidence → Debate → Reproducibility → Radar → Experts → Venues → Sources → Q&A.
5. The report is saved to **Research History**.
6. Reopen a saved report without repeating searches.
7. Export Markdown, JSON, or PDF. Copy BibTeX from Novelty when metadata exists.
8. Optionally compare two saved reports.

## Data and grounding limitations

- Fixture titles used for offline examples are **illustrative search-result shapes**. They are not a live index and must not deep-link to unrelated real papers. Unverified URLs are shown as text, not as citations.
- Live results keep the URL returned with that result.
- Scholar “cited by” graphs are not fully expanded in the default query budget.
- Author emails are not scraped; any introduction text is a **draft** and is never sent.
- Venue deadlines appear only when the snippet or title contains an explicit date.
- Language-model analysis can still mis-tag stance; grounding prevents invented IDs, not bad reasoning about real snippets.

## Q&A grounding

The assistant answers only from the current report and evidence store. Out-of-scope questions receive: *I don't have enough evidence in this report to answer that.* Cited source IDs are validated before they are shown.

## History

Each successful analysis inserts a row into the `runs` table of the same SQLite file as the search cache. Reloading reads stored JSON. **Clear History** deletes `runs` only; the search cache table is left intact.

## Export

- Markdown: executive summary plus all report sections
- JSON: serialized report and evidence items
- PDF: text rendering of the Markdown report
- BibTeX: closest-work fields that exist in the store; missing fields use placeholders such as `AUTHOR-UNKNOWN`

## Security

- API keys live in environment variables or the host secret manager
- `.env` and `.streamlit/secrets.toml` are gitignored
- The UI does not display keys, search-budget counters, or provider billing

## Testing

```bash
python -m pytest -q
```

## AI tools used in development

- Cursor Grok 4.6 (cloud agent) — scaffolding, implementation, tests, and docs
- Search-engine public documentation — parameter and response-shape checks
- Optional Anthropic Messages API for live analysis via the official SDK

## License

MIT. See `LICENSE`.
