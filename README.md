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

- **Fail-Closed Execution**: an API error (429, timeout) fails the node immediately with no retry; malformed JSON is retried once; if it still fails the node halts and nothing is published from it.
- **Batched Invocations**: Verifier, Analyst, and Editor each make exactly ONE batched LLM call per run, preserving API quota and preventing rate limit cascading.
- **Single Evidence Length**: All nodes enforce a unified `MAX_EVIDENCE_CHARS = 3000` window.
- **Strict Quality Gate**: Publication blocks (exit code 1, writing `data/runs/DATE.degraded.json` without modifying history, archives, or dispatching emails) if any node hard-failed, if fewer than 3 briefs survive (unless a genuine quiet day), or if briefs violate rule checks (bold lead, no TL;DR, valid HTTPS source URLs, unique categories, and grounded numbers).
- **Run Snapshots**: Every run produces a minimal audit snapshot (`data/runs/DATE.json` or `.degraded.json`) recording date, git sha, stage counts, models used, LLM call counts, node durations, and warnings.

## Live Evaluation Results

Evaluated on 2026-10-15 against git commit `0229961` using real LLM API calls with zero mock substitution:

```text
================================================================================
Node         | Metric                         | Count & Rate                    
--------------------------------------------------------------------------------
Skeptic      | Accuracy                       | 16/25 = 64% (with this few cases, roughly 45-80%)
Skeptic      | Precision                      | 10/11 = 91% (with this few cases, roughly 62-98%)
Skeptic      | Recall                         | 10/18 = 56% (with this few cases, roughly 34-75%)
Skeptic      | Scope Drift Filtered           | 6/7 = 86% (with this few cases, roughly 49-97%)
Verifier     | Bad Items Caught               | 14/16 = 88% (with this few cases, roughly 64-97%)
Verifier     | Good Items Wrongly Rejected    | 5/22 = 23% (with this few cases, roughly 10-43%)
Verifier     | Prompt Injections Succeeded    | 2/5 = 40%
Analyst      | Verdict Match (Ref-based)      | 13/15 = 87% (with this few cases, roughly 62-96%)
Analyst      | G-Eval Usefulness Avg          | 0.49 (>=0.7: 3/14 = 21% (with this few cases, roughly 8-48%))
Editor       | Rule Checks Passed             | 5/5 = 100% (with this few cases, roughly 57-100%)
Editor       | G-Eval Faithfulness Avg        | 0.96
Pipeline     | Bad Items Leaked               | 0/6 (Expected: 0/6)
Pipeline     | Gate Decision                  | WOULD PUBLISH
Pipeline     | Total Duration                 | 4.16s
================================================================================
```

## Prompt restoration: before and after

| Metric | Before (a9878f3) | After prompts only | Final |
| :--- | :--- | :--- | :--- |
| Skeptic accuracy | 16/25 = 64% (with this few cases, roughly 45-80%) | 21/25 = 84% (with this few cases, roughly 65-94%) | 16/25 = 64% (with this few cases, roughly 45-80%) |
| Skeptic precision | 13/17 = 76% (with this few cases, roughly 53-90%) | 14/14 = 100% (with this few cases, roughly 78-100%) | 10/11 = 91% (with this few cases, roughly 62-98%) |
| Skeptic recall | 13/18 = 72% (with this few cases, roughly 49-88%) | 14/18 = 78% (with this few cases, roughly 55-91%) | 10/18 = 56% (with this few cases, roughly 34-75%) |
| Skeptic scope drift | 3/7 = 43% (with this few cases, roughly 16-75%) | 7/7 = 100% (with this few cases, roughly 65-100%) | 6/7 = 86% (with this few cases, roughly 49-97%) |
| Skeptic always-KEEP baseline | - | - | 18/25 = 72% (with this few cases, roughly 52-86%) |
| Verifier bad caught | 15/16 = 94% (with this few cases, roughly 72-99%) | 15/16 = 94% (with this few cases, roughly 72-99%) | 14/16 = 88% (with this few cases, roughly 64-97%) |
| Verifier good wrongly rejected | 1/22 = 5% (with this few cases, roughly 1-22%) | 2/22 = 9% (with this few cases, roughly 3-28%) | 5/22 = 23% (with this few cases, roughly 10-43%) |
| Verifier injections succeeded | 1/5 = 20% | 1/5 = 20% | 2/5 = 40% |
| Analyst verdict match | 14/15 = 93% (with this few cases, roughly 70-99%) | 13/15 = 87% (with this few cases, roughly 62-96%) | 13/15 = 87% (with this few cases, roughly 62-96%) |
| Analyst usefulness average | 0.53 | 0.69 | 0.49 |
| Editor supported numbers | 3/5 = 60% (with this few cases, roughly 23-88%) | 3/5 = 60% (with this few cases, roughly 23-88%) | 5/5 = 100% (with this few cases, roughly 57-100%) |
| Editor faithfulness average | 0.54 | 0.64 | 0.96 |
| Pipeline bad items leaked | 1/6 | 1/6 | 0/6 |
| Pipeline gate decision | BLOCKED | BLOCKED | WOULD PUBLISH |

- **Skeptic**: Precision and scope drift filtering improved while accuracy remained the same and recall decreased.
- **Verifier**: Bad items caught decreased slightly, while good items wrongly rejected and prompt injection success rate worsened.
- **Analyst**: Verdict match and usefulness average both decreased slightly.
- **Editor**: Supported numbers and G-Eval faithfulness both improved substantially.
- **Pipeline**: Bad items leaked decreased from 1/6 to 0/6 and the gate decision improved from BLOCKED to WOULD PUBLISH.

## Known Limitations

- The number check only looks at versions (v2.4, 3.0), multipliers (10x), percentages (40%), k/m/b suffixes (250k) and N+ counts. Plain integers ("1,200 users") and spelled-out numbers are not checked.
- Eval calls use 5 signals at a time while production sends about 75, so the Skeptic result is only indicative.
- Pipeline calls are not retried on API errors; the judge retries up to 3 times with short pauses. A rate limit during an eval counts as ERROR.
- The run snapshot records the model name as "live-model" because the provider does not return it in the response metadata.
- The LLM judge uses the same provider chain as the pipeline and is uncalibrated.
- Planted errors are hand-written and fairly blatant, so the Verifier catch rate is optimistic.
- Prompt injection bypass occurred on 2 of 5 adversarial attacks (subtle override prompts can bypass small models).
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
