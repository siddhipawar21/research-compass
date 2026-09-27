# Research Compass

Research Compass turns a research abstract into a **grounded research intelligence report** covering novelty, supporting and contradicting evidence, debate, reproducibility, topic radar, experts, venues, sources, and a grounded Q&A assistant.

The application is designed around one principle: **research claims should stay connected to the evidence that supports them.**

## What problem does it solve?

Literature review for a new research idea is slow, and language models can produce unsupported papers or citations.

Research Compass creates an auditable research dossier showing:

- what related work exists
- what evidence supports or contradicts the idea
- where the literature agrees or disagrees
- how reproducible the evidence appears
- which topics, experts, and venues are relevant
- which sources support each claim

## Core idea

Research Compass uses a **search-backed report** as the unit of work.

The analysis modules reason over retrieved evidence rather than inventing papers, URLs, authors, or dates. Each evidence item receives a source ID such as `SRC-001`, and claims are tied back to those stored source records.

When evidence is insufficient, the report states that rather than filling the gap with unsupported information.

## Features

- **Novelty analysis** — identifies related and potentially overlapping work
- **Evidence analysis** — organizes supporting and contradicting evidence
- **Debate view** — summarizes areas of agreement and disagreement
- **Reproducibility analysis** — examines available methodological evidence
- **Topic Radar** — surfaces important research themes
- **Experts** — identifies relevant researchers from retrieved evidence
- **Venues** — identifies relevant publication venues
- **Sources** — displays the evidence behind the report
- **Grounded Q&A** — answers questions using the current report and evidence store
- **Evidence weights** — visualizes the existing source-quality weighting rule
- **Research History** — stores successful reports locally
- **Report comparison** — compares two saved reports descriptively
- **Research connections** — shows relationships among the report's closest works and cited source IDs
- **Exports** — Markdown, JSON, PDF, and BibTeX
- **Light theme** by default, with optional dark theme

## Architecture

```text
Research Abstract
       |
       v
Query Planner
       |
       v
Search Client
(SQLite cache + retries + per-run cap)
       |
       v
Evidence Store
(normalized SRC-xxx records)
       |
       v
Analysis Modules
       |
       +--> Novelty
       +--> Evidence
       +--> Debate
       +--> Reproducibility
       +--> Radar
       +--> Experts
       +--> Venues
       +--> Grounded Q&A
       |
       v
Streamlit Report
       |
       +--> History
       +--> Compare
       +--> Export
```

## Grounding and source integrity

Research Compass keeps source metadata together in the evidence store.

Important rules:

- URLs come from retrieved search results rather than being constructed from titles or IDs.
- Titles and URLs remain paired with the same evidence record.
- Unknown source IDs are rejected.
- The language model may not introduce new papers, URLs, authors, or dates.
- If a source URL cannot be verified, it is not presented as a verified citation.
- Fixture/demo data is intended for offline product review and is not a live literature index.
- Venue deadlines are shown only when an explicit date is present in the retrieved evidence.

## Setup

### Requirements

- Python 3.11+
- Git
- A SerpApi API key for live literature search
- An Anthropic API key is optional for model-powered analysis

### Clone the repository

```bash
git clone https://github.com/siddhipawar21/research-compass.git
cd research-compass
```

### Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Configure environment variables

Copy the example environment file:

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Then add your credentials to `.env`:

```text
SERPAPI_API_KEY=your_serpapi_key
ANTHROPIC_API_KEY=your_anthropic_key
```

`ANTHROPIC_API_KEY` is optional.

**Never commit real API keys to GitHub.**

The repository's `.gitignore` excludes `.env`, local virtual environments, cache/database files, and Streamlit secrets.

## Running locally

Start the application with:

```bash
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

### Demo Mode

The application includes bundled search-shaped fixtures for offline review.

An example abstract can be analyzed without live search credentials.

### Live Mode

For a custom abstract and live literature retrieval, configure:

```text
SERPAPI_API_KEY=your_serpapi_key
```

The search client retrieves real search results and stores their returned metadata.

## Deployment — Streamlit Community Cloud

Research Compass can be deployed from the public GitHub repository.

1. Open [Streamlit Community Cloud](https://share.streamlit.io/).
2. Create a new app.
3. Select the GitHub repository: `siddhipawar21/research-compass`.
4. Select branch: `main`.
5. Set the main file to: `app.py`.
6. Deploy the application.
7. Open the application's **Secrets** settings.
8. Add the required credentials there.

Example Streamlit secrets:

```toml
SERPAPI_API_KEY = "your_serpapi_key"
ANTHROPIC_API_KEY = "your_anthropic_key"
```

Do **not** replace the example values in this README with real keys.

Streamlit Cloud provides secrets to the application as environment variables. API keys should never be committed to the repository or displayed in the application interface.

## Research workflow

1. Open Research Compass.
2. Paste a research abstract or load an example.
3. Click **Analyze Research**.
4. Review Novelty, Evidence, Debate, Reproducibility, Radar, Experts, Venues, Sources, and Q&A.
5. Save and reopen reports through **Research History**.
6. Compare saved reports when needed.
7. Export the report as Markdown, JSON, or PDF.
8. Copy BibTeX information when publication metadata is available.

## Q&A grounding

The research assistant is restricted to the current report and evidence store.

If the available evidence does not support a question, the assistant responds that there is not enough evidence in the current report rather than fabricating an answer.

Source IDs referenced by the assistant are validated against the stored evidence before being displayed.

## History

Successful analyses are stored in the application's SQLite database.

History allows users to:

- reopen previous reports
- review previously retrieved evidence
- compare saved reports
- avoid repeating the same searches unnecessarily

Clearing report history removes saved runs while preserving the search-cache data.

## Exports

Research Compass supports:

- **Markdown** — executive summary and report sections
- **JSON** — serialized report and evidence records
- **PDF** — formatted report
- **BibTeX** — closest-work metadata when available

Missing publication metadata is not invented.

## Data and grounding limitations

- Demo fixtures are illustrative search-result shapes for offline review.
- Demo records are not a live literature index.
- Live results retain the URL returned by the search provider.
- Citation graphs are not intended to represent a complete scholarly citation network.
- Author contact information is not scraped.
- Venue deadlines are reported only when an explicit date is available in the retrieved evidence.
- Language-model reasoning can still misinterpret the stance of a source; grounding reduces unsupported source generation but does not guarantee perfect interpretation.

## Security

- API keys are stored in environment variables or the deployment platform's secret manager.
- `.env` and `.streamlit/secrets.toml` are excluded from Git.
- API keys are not displayed in the UI.
- Provider billing information and internal search-budget details are not exposed to normal users.

## Testing

Run the test suite with:

```bash
python -m pytest -q
```

The repository includes tests covering grounding, source integrity, exports, history, Q&A, search caching, storage, themes, venues, and demo behavior.

## AI tools used in development

- Cursor / Grok — implementation, scaffolding, tests, and documentation
- Search-engine public documentation — search parameter and response-shape verification
- Anthropic Messages API — optional grounded analysis through the official SDK

## License

MIT License. See [`LICENSE`](LICENSE).

## Repository

GitHub: https://github.com/siddhipawar21/research-compass
