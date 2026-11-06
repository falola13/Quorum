# Quorum Roadmap

Constraint: free models only. Quorum runs on free-tier LLMs and search APIs. The scarce
resource is rate limits and daily quota, not money. So "cost" in this roadmap means

## The unique angle: consensus-verified claims

The project is already called *Quorum*. Build it to live up to the name.

**Idea:** most research agents produce fluent reports with a list of URLs at the bottom. Nobody
checks whether URL #3 actually says what sentence #7 claims. Quorum's differentiator is a
**claim ledger**:

1. **Extract** the report's atomic, checkable claims (for example, "X grew 23% in 2025").
2. **Verify** each claim against the scraped source text. An LLM judge returns

   `SUPPORTS | CONTRADICTS | NOT_FOUND` along with the exact supporting quote.
3. **Require a quorum:** a claim counts as *verified* only if ≥ N **independent** sources support it.

   "Independent" means different registrable domains, and a source isn't independent if it
          republishes another source (detected with near-duplicate text similarity).
4. **Report honestly.** The final output has three sections:
   - **Verified** — meets the quorum, with inline citations and quotes
   - **Single-source** — supported by only one source, clearly labelled
   - **Contested** — sources disagree, and both sides are shown

Why this sets you apart:

- It targets hallucination, which is the main problem in production LLM systems.
- It can be measured (see Phase 2), so it isn't just a vibe.
- The "contested" section is a feature almost no research agent offers. Showing disagreement is
more useful than a confident summary.
- It makes a strong demo: a report where every sentence is colour-coded by verification status.

---

## Phase 0: Make the current code honest and solid (1–2 days)

Do this first. Reviewers read your code, not just your README.

- [x] **Fix a context-loss bug:** `pipeline.py` passes `search_results[:800]` to the reader.
  ```
  That's roughly 1–2 results, so the reader never sees most of what search found.
  ```
- [x] The pipeline tells the reader to scrape "the most relevant URL" while `READER_PROMPT` says
  ```
  "2–3 URLs". Pick one.
  ```
- [x] Every stage banner prints "step 1", and the critic banner says "Writer is drafting". Fix the labels.
- [x] `except Exception as e: print(e)` swallows errors and returns `None`. Raise a typed error or
  ```
  return partial state with an `error` field.
  ```
- [ ] Use `logging` in library code and keep `rich` output for the CLI layer.
- [x] Remove committed `__pycache__/` and add it to `.gitignore`.
- [x] Choose one source of truth for dependencies (`pyproject.toml` + `uv.lock`) and generate
  ```
  `requirements.txt` from it or delete it. Python is `>=3.12` but the committed `.pyc` files are
  3.11; make them consistent.
  ```
- [x] Delete or implement the `src/quorum` stub and the empty `app.py`.
- [ ] Take the topic from the command line (`quorum "your topic"`) instead of editing `main.py`.
- [ ] Return a typed result (a Pydantic `ResearchResult`) instead of an untyped dict.

## Phase 1: A real agent graph (about 1 week)

Replace the linear script with an explicit state machine (LangGraph fits the existing stack).

- [ ] **Planner node:** break the topic into 3–5 sub-questions.
- [ ] **Parallel researchers:** one search + read branch per sub-question, run concurrently.
- [ ] **Critic → revise loop:** if the critic score is below a threshold, send specific feedback
  ```
  to the writer. Cap the loop at 2 revisions so it can't run forever or burn money.
  ```
- [ ] **Structured outputs everywhere:** Pydantic schemas for search hits, extracted facts, and the
  ```
  critique, instead of parsing free text like `Score: X/10`.
  ```
- [ ] **Per-run budget:** max LLM calls, max tool calls, and max tokens, enforced in the graph.
  ```
  Every revision loop and parallel branch multiplies requests against the free-tier limit.
  ```
- [ ] **Rate-limit handling:** retry with exponential backoff on 429 errors, and limit how many
  ```
  parallel branches run at once, so a run slows down instead of crashing.
  ```

*Interview talking point:* "Why a graph and not a free-form agent swarm?" Predictability, bounded
cost, and testable nodes.

## Phase 2: Evaluation harness (about 1 week). This is the biggest edge.

Most portfolio projects have no evals. Having them signals that you understand production AI.

- [ ] Build an eval set of 30–50 research questions with known answers. Write some yourself and
  ```
  take some from a public multi-hop QA benchmark.
  ```
- [ ] Metrics:
  - **Citation precision:** of the claims that have citations, what % does the cited source
  actually support? (Measured with the Phase 3 verifier and a hand-labelled sample to validate
  the judge.)
  - **Answer correctness** against the reference answers
  - **LLM calls and tokens per report**, plus **latency** (p50/p95)
  - **Source diversity:** the number of unique domains per report
- [ ] `quorum eval` command that writes a results table. Run it in CI on a small subset.
- [ ] **Quota planning:** a full eval run (50 questions × about 10 LLM calls each) can use up a
  ```
  day's free quota. Build caching (Phase 4) before running the full set, and keep a 10-question
  "smoke" subset for day-to-day work.
  ```
- [ ] **Publish the before/after:** "baseline pipeline: X% citation precision → with claim
  ```
  verification: Y%". That one number is the headline of your portfolio.
  ```

## Phase 3: Claim ledger and quorum verification (1–2 weeks)

Build the unique angle described above.

- [ ] Claim extraction node (structured output: a list of atomic claims)
- [ ] Verifier node: claim + source chunk → verdict + quote. Use a small, cheap model here and
  ```
  measure how well it agrees with your hand labels.
  ```
- [ ] Source independence: domain dedup plus near-duplicate detection (MinHash or embedding similarity)
- [ ] Configurable quorum (`--quorum 2`)
- [ ] When a claim fails, re-search for more evidence first, then drop or downgrade it.
- [ ] Report renderer with Verified / Single-source / Contested sections

## Phase 4: Make it usable and observable (about 1 week)

- [ ] **FastAPI** backend with **SSE streaming** of node-by-node progress (FastAPI is already a dependency)
- [ ] **Streamlit** UI (already a dependency): live agent timeline, a report where you can hover a
  ```
  claim to see its quotes, and a cost/latency panel
  ```
- [ ] **Tracing:** LangSmith or OpenTelemetry, with one trace per run, tokens per node, and tool errors
- [ ] **Caching:** cache search and scrape results by URL/query so re-runs and evals are cheap
- [ ] **Model routing:** the smallest free model that's good enough for extraction and
  ```
  verification, and a stronger free model for writing (each model usually has its own quota).
  Show the calls/quality trade-off with the eval harness.
  ```

## Phase 5: Ship it (2–3 days)

- [ ] Dockerfile and a free-tier deploy (Hugging Face Spaces or Streamlit Community Cloud), with
  ```
  per-visitor rate limiting so a public demo can't use up your quota. Consider a "replay mode"
  that shows cached example runs when the quota is gone.
  ```
- [ ] Unit tests for tools (mock HTTP), node tests with fake LLMs, and a GitHub Actions CI badge
- [ ] A 2-minute demo video or GIF at the top of the README
- [ ] A short write-up or blog post: "How I measured and cut citation hallucinations in a research
  ```
  agent from X% to Y%"
  ```





