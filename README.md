# DailyDiff

Autonomous tech curation pipeline (LangGraph + FastAPI + React) designed for computer science students and software engineers. It scans open-source codebases, developer releases, and tech forums, filtering out enterprise marketing fluff and dense academic theory into concise, actionable developer briefs.

## Architecture

```
Scout (Ecosystem Signals)
  │
  ▼
Skeptic (Deduplication & Scope Filtering)
  │
  ▼
Researcher (Documentation Scraper)
  │
  ▼
Verifier (Fact-Checking & Anti-Hype in 1 Batched LLM Call)
  │
  ▼
Analyst (Pedagogical Utility & Audience in 1 Batched LLM Call)
  │
  ▼
Editor (Curation, Formatting & Category Balance in 1 Batched LLM Call)
  │
  ▼
Quality Gate (Strict Verification & Publication Snapshot)
```

## Reliability Design

- **Fail-Closed Execution**: If any node encounters an unrecoverable API error or malformed JSON after one retry, it halts immediately without publishing degraded content or generic fallback text.
- **Batched Invocations**: Verifier, Analyst, and Editor each make exactly ONE batched LLM call per run, preserving API quota and preventing rate limit cascading.
- **Single Evidence Length**: All nodes enforce a unified `MAX_EVIDENCE_CHARS = 3000` window.
- **Strict Quality Gate**: Publication blocks (exit code 1, writing `data/runs/DATE.degraded.json` without modifying history, archives, or dispatching emails) if any node hard-failed, if fewer than 3 briefs survive (unless a genuine quiet day), or if briefs violate rule checks (bold lead, no TL;DR, valid HTTPS source URLs, unique categories, and grounded numbers).
- **Run Snapshots**: Every run produces a minimal audit snapshot (`data/runs/DATE.json` or `.degraded.json`) recording date, git sha, stage counts, models used, LLM call counts, node durations, and warnings.

## Live Evaluation Results

Evaluated on 2026-10-14 against git commit `a9878f3` using real LLM API calls with zero mock substitution:

```text
================================================================================
Node         | Metric                         | Count & Rate                    
--------------------------------------------------------------------------------
Skeptic      | Accuracy                       | 16/25 = 64% (with this few cases, roughly 45-80%)
Skeptic      | Precision                      | 13/17 = 76% (with this few cases, roughly 53-90%)
Skeptic      | Recall                         | 13/18 = 72% (with this few cases, roughly 49-88%)
Skeptic      | Scope Drift Filtered           | 3/7 = 43% (with this few cases, roughly 16-75%)
Verifier     | Bad Items Caught               | 15/16 = 94% (with this few cases, roughly 72-99%)
Verifier     | Good Items Wrongly Rejected    | 1/22 = 5% (with this few cases, roughly 1-22%)
Verifier     | Prompt Injections Succeeded    | 1/5 = 20%
Analyst      | Verdict Match (Ref-based)      | 14/15 = 93% (with this few cases, roughly 70-99%)
Analyst      | G-Eval Usefulness Avg          | 0.53 (>=0.7: 5/15 = 33% (with this few cases, roughly 15-58%))
Editor       | Rule Checks Passed             | 5/5 = 100% (with this few cases, roughly 57-100%)
Editor       | G-Eval Faithfulness Avg        | 0.54
Pipeline     | Bad Items Leaked               | 1/6 (Expected: 0/6)
Pipeline     | Gate Decision                  | BLOCKED
Pipeline     | Total Duration                 | 8.6s
================================================================================
```

## Known Limitations

- LLM Judge calls use the same provider chain as the pipeline; the judge is uncalibrated.
- Prompt injection bypass occurred on 1 of 5 adversarial attacks (subtle override prompts can bypass small models).
- Free-tier rate limits (15 RPM on Google Gemini) require exponential backoff delays during large evaluation runs.
- The numeric consistency rule flags valid numbers if the model rewrites exact evidence figures (e.g., '250k' vs 'quarter million').
- Scope drift filtering occasionally admits niche enterprise infrastructure when described as developer tools.

## Running Tests & Evals

### Offline Unit Tests
```bash
PYTHONPATH=backend pytest tests -m "not live" -q
```

### End-to-End Evaluation Suite
Requires `GEMINI_API_KEY`, `MISTRAL_API_KEY`, or `GROQ_API_KEY` in `.env`:
```bash
python tests/evals/run_evals.py
```
Individual component evaluations can also run standalone:
```bash
python tests/evals/eval_skeptic.py
python tests/evals/eval_verifier.py
python tests/evals/eval_analyst.py
python tests/evals/eval_editor.py
python tests/evals/eval_pipeline.py
python tests/evals/eval_history.py
```

### Frontend Build
```bash
cd frontend && npm run build
```
