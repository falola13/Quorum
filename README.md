# Quorum

Quorum is a multi-agent research assistant. You give it a topic; agents search the web, read the
most relevant pages, write a structured report with sources, and then critique that report.

The long-term goal — and the reason for the name — is **consensus-verified research**: no claim
reaches the final report unless a *quorum* of independent sources supports it, and disagreements
are surfaced instead of smoothed over. See [docs/ROADMAP.md](docs/ROADMAP.md) for the plan.

> **Status: early prototype (v0.1).** The linear pipeline below works end to end from the CLI.
> The UI, API, verification layer, and evals are planned, not built.

## How it works today

```
topic ─► Search agent ─► Reader agent ─► Writer chain ─► Critic chain ─► report + critique
          (tool: search)  (tool: scrape_url)
```

| Stage | Type | What it does | Code |
|---|---|---|---|
| Search | Tool-calling agent | Queries the web, re-searches if results are thin, returns title/URL/summary per hit | [src/agents/agents.py](src/agents/agents.py) |
| Reader | Tool-calling agent | Picks the 2–3 best URLs, scrapes them, extracts key facts per source | [src/agents/agents.py](src/agents/agents.py) |
| Writer | LLM chain | Turns search results + scraped content into Introduction / Key Findings / Conclusion / Sources | [src/agents/agents.py](src/agents/agents.py) |
| Critic | LLM chain | Scores the report out of 10 and lists strengths and weaknesses | [src/agents/agents.py](src/agents/agents.py) |
| Orchestration | Plain Python | Runs the stages in order and collects results in a `state` dict | [src/pipelines/pipeline.py](src/pipelines/pipeline.py) |

### Tools ([src/tools/tools.py](src/tools/tools.py))

- **`search`**: uses a fallback chain of search providers so a missing key or rate limit doesn't
  kill a run: **Tavily → Exa → DuckDuckGo**. Providers without an API key are skipped. DuckDuckGo
  needs no key, so search always has a last resort.
- **`scrape_url`**: fetches a page and tries three extraction strategies in order:
  **trafilatura** (articles/blogs) → **readability** + BeautifulSoup cleanup → **full-page text**
  with nav, footer, script, and similar tags removed. Non-HTML responses are skipped, and output is
  capped at 5,000 characters to keep the LLM context small.

### Stack

- **LLM:** Google Gemini via `langchain-google-genai` (temperature 0)
- **Agent framework:** LangChain 1.x (`create_agent`, LCEL chains)
- **Search:** Tavily, Exa, DuckDuckGo (`ddgs`)
- **Extraction:** trafilatura, readability-lxml, BeautifulSoup
- **Packaging:** `uv` with `pyproject.toml` (Python 3.12+)

## Getting started

### 1. Clone

```bash
git clone <repo-url>
cd Quorum
```

### 2. Install (uv, recommended)

```bash
uv sync
```

Or with pip (Python 3.12+):

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 3. Configure API keys

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=...        # required: Gemini
TAVILY_API_KEY=...        # optional: primary search provider
EXA_API_KEY=...           # optional: secondary search provider
SEARCH_PROVIDER=auto      # auto | tavily | exa | ddg

```

Without Tavily or Exa keys, search falls back to DuckDuckGo.

### 4. Run

Edit the `topic` in [main.py](main.py), then:

```bash
uv run python main.py
```

Each stage's output is printed to the terminal as it finishes.

## Project layout

```
Quorum/
├── main.py                 # CLI entry point
├── app.py                  # (planned) UI / API entry point
├── src/
│   ├── agents/agents.py    # LLM setup, agent builders, writer & critic chains
│   ├── pipelines/pipeline.py  # stage orchestration
│   └── tools/tools.py      # search + scrape tools with fallbacks
├── docs/ROADMAP.md         # what's next and why
├── pyproject.toml / uv.lock
└── requirements.txt
```

## Known limitations

These are known and tracked in the roadmap (Phase 0):

- The pipeline is strictly linear. The critic's score is not used to trigger a revision.
- The writer lists sources but does not tie each claim to the source that supports it.
- The reader only gets the first 800 characters of the search results, so it usually sees just 1–2 hits.
- There are no tests or evaluations yet, so quality isn't measured.

## License

See [LICENSE](LICENSE).
