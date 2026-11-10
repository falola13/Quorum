# Quorum

Quorum is a multi-agent research assistant. You give it a topic; agents search the web, read the
most relevant pages, write a structured report with sources, and then critique that report.

The long-term goal — and the reason for the name — is **consensus-verified research**: no claim
reaches the final report unless a *quorum* of independent sources supports it, and disagreements
are surfaced instead of smoothed over. See [docs/ROADMAP.md](docs/ROADMAP.md) for the plan.

> **Status: early prototype (v0.1).** A CLI pipeline with citations checking works today.
> The UI, API, verification layer, and evals are planned, not built.

## How it works today

```
topic ─► Search agent ─► Selector ─► Scraper (code) ─► Writer chain ─► Citations check (code) ─► Critic  ─► report + critique
          (tool: search)  ****
```

| Stage                 | Type               | What it does                                                                                            | Code                                                   |
| --------------------- | ------------------ | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| Search                | Tool-calling agent | Queries the web, re-searches if results are thin, returns title/URL/snippet per hit                     | [src/agents/agents.py](src/agents/agents.py)           |
| Selector              | LLM chain          | Picks the 5 out of the reliable results,rank them by the best and return their IDs                      | [src/agents/agents.py](src/agents/agents.py)           |
| Scraper (code)        | Plain Python       | Scrape the web for more content using the search results and the selected IDs,returns id/title/url/kind | [src/pipelines/pipeline.py](src/pipelines/pipeline.py) |
| Writer                | LLM chain          | Writes a detailed research using the scraped results . returns a cited report                           | [src/agents/agents.py](src/agents/agents.py)           |
| Citation check (code) | Plain Python       | Checks whether the result cited the sources it listed and whether all source were cited                 | [src/helper/helper.py](src/helper/helper.py)           |
| Critic                | LLM chain          | markdown Scores the report out of 10 and lists strengths and                                            | [src/agents/agents.py](src/agents/agents.py)           |

## Design Decisions

- **The LLM picks sources by ID; code looks up the URLs**. When the model retyped URLs, it sometimes dropped or changed them. Now it only returns numbers like [4, 1, 5], code checks those numbers against the real results, and the URLs come straight from the search data, so the model can't invent one. 
- **Search results reach code through the tool's artifact**. LLM retypes the search results and doesnt return the desired output in the content. Using a structured response output costs more and adds latency.
- **The scraper falls back to labelled snippets**. Some Client users block bots from scraping their websites and some pages contains PDFs which returns None. Habing 3 out of 5 failed in the urls passed. LLM has little results to work with it. Hence the need to return the snippet rather than the scraped page. (snippet only) tag is added and it moves to the bottom of the ranked list. 
- **The Sources section is built by code, and citations are checked**: The LLM list sources it never used or read in its report.
- **Fail fast on bad settings**. Wrong credentials or missing credentials **fall back** to the next provider.  fail fast on bad setting (a `SEARCH_PROVIDER` typo) and when no source at all could be scraped.
- **Built for free-tier limits**. Limited number of searches. Less tool calls and retries from the LLM.

## Results so far

|   | **First run** | Now |
| - | ------------- | --- |
| LLM calls | 9 | 7 |
| Sources the writer cited but never read | 9 | 0 |
| Where the Sources list comes from | the LLM | code | 
| Citation check | none | automatic |
| Tests | 0 | 12 | 

Baseline run: [docs/runs/2026-11-06-baseline.md](docs/runs/2026-11-06-baseline.md)

### Tools ([src/tools/tools.py](src/tools/tools.py))

- `search`: uses a fallback chain of search providers so a missing key or rate limit doesn't
kill a run: **Tavily → Exa → DuckDuckGo**. Providers without an API key are skipped. DuckDuckGo
needs no key, so search always has a last resort.
- `scrape_page`: fetches a page and tries three extraction strategies in order:
**trafilatura** (articles/blogs) → **readability** + BeautifulSoup cleanup → **full-page text**
with nav, footer, script, and similar tags removed. Non-HTML responses are skipped, and output is
capped at 5,000 characters to keep the LLM context small. Code calls it instead of LLM.

### Stack

- **LLM:** Google Gemini via `langchain-google-genai` 
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

### 5. Run the tests

The test makes use of no API calls and the command

```bash
uv run pytest
```

## Project layout

```
Quorum/
├── main.py                 # CLI entry point
├── app.py                  # (planned) UI / API entry point
├── tests/                  # pytest run 
├── docs/
│   ├── ROADMAP.md # what's next and why
│   └── runs/ 
├── src/
│   ├── agents/agents.py    # LLM setup, agent builders, writer & critic chains
│   ├── pipelines/pipeline.py  # stage orchestration
│   ├── helper/helper.py  # pure helper function
│   └── tools/tools.py      # search + scrape tools with fallbacks
├── pyproject.toml / uv.lock
└── requirements.txt
```

## Known limitations

These are known and tracked limitations:

- The pipeline is strictly linear. The critic's score is not used to trigger a revision.
- claims are cited but not yet **checked against the source text**
- the report often relies on ine secondary source (like a blog summarising others)
- DuckDuckGo is unreliable, and many sites block scrapers (403), so PDFs are skipped

## License

See [LICENSE](LICENSE).
