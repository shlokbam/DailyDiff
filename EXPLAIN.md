# DailyDiff: System Architecture, Evaluation & Study Guide

This document is a study guide for computer science students and engineers preparing for AI engineering and multi-agent systems interviews.

---

## 1. The Pipeline in Six Lines

1. **Scout** gathers raw tech signals from GitHub search, Hacker News, Dev.to, freeCodeCamp, Product Hunt, Reddit (/r/webdev), and framework releases.
2. **Skeptic** deduplicates against historical URLs and filters out enterprise, financial, and dense academic noise.
3. **Researcher** fetches repository documentation and release notes up to a strict 3,000-character limit.
4. **Verifier** fact-checks candidate descriptions against documentation in a single batched LLM call, dropping unverifiable items.
5. **Analyst** determines practical developer utility, target audience, and actionable verdicts (WATCH, INTEGRATE, READ) in one batched call.
6. **Editor** selects up to 5 items, formats bold lead sentences, assigns unique categories, and hands them to the Quality Gate.

---

## 2. File Directory & Component Responsibilities

| File | Purpose |
|---|---|
| `backend/run_agent.py` | Orchestrates pipeline execution, executes the quality gate, and writes execution audit snapshots. |
| `backend/app/checks.py` | Deterministic quality validation rules (bold lead, no TL;DR, HTTPS URLs, category uniqueness, numeric grounding). |
| `backend/app/run_health.py` | Runtime telemetry: tracks node latency, model names, LLM call counts, hard fallbacks, and soft warnings. |
| `backend/app/database.py` | Subscriber database management (SQLite/Postgres) and archive history reader. |
| `backend/app/config.py` | Environment variable loader, API key bindings, and provider fallback defaults. |
| `backend/app/main.py` | FastAPI server exposing subscription endpoints and serving the static React frontend. |
| `backend/app/agents/graph.py` | LangGraph StateGraph compiling the multi-agent nodes into an executable workflow. |
| `backend/app/agents/models.py` | Multi-provider LLM chain (Groq -> Gemini -> Mistral), 30s timeouts, single-retry JSON parser, and XML escaping. |
| `backend/app/agents/state.py` | TypedDict schema defining candidate flow through graph nodes. |
| `backend/app/agents/scout.py` | Ecosystem scraper parsing Atom/RSS feeds, GitHub repos, and framework releases. |
| `backend/app/agents/skeptic.py` | Deduplication engine and relevance filter for student/developer utility. |
| `backend/app/agents/researcher.py` | Scrapes documentation for vetted candidates with `MAX_EVIDENCE_CHARS = 3000`. |
| `backend/app/agents/verifier.py` | Batched LLM fact-checking agent rejecting ungrounded claims and prompt injections. |
| `backend/app/agents/analyst.py` | Batched LLM assessment generating developer takeaways, target audiences, and verdicts. |
| `backend/app/agents/editor.py` | Batched LLM editorial agent formatting briefs into designated categories. |
| `tests/conftest.py` | Adds the repo root and backend/ to the Python path so the tests can import the code. |
| `tests/test_checks.py` | Unit tests for every individual quality check with valid and invalid counter-examples. |
| `tests/test_gate.py` | Tests publication gate blocking on fallbacks, drops, quiet days, and min-brief thresholds. |
| `tests/test_nodes.py` | Tests fail-closed behavior on API error, single JSON retry, missing evidence drops, and tag escaping. |
| `tests/test_scout_parsing.py` | Unit tests verifying safe XML parsing of Atom feeds, RSS, and releases with null bodies. |
| `tests/test_no_fake_results.py` | Regression test ensuring simulated scores, fake fallbacks, and hardcoded tables never return. |
| `tests/evals/golden_dataset.json` | 25 curated reference cases with ground-truth expectations across all pipeline stages. |
| `tests/evals/planted_errors.json` | 13 hand-written subtle error cases (exaggerations, wrong numbers, unsupported features, injections). |
| `tests/evals/common.py` | Dataset loader, Wilson score confidence interval helper `rate(k, n)`, and regression comparison. |
| `tests/evals/judge.py` | LLM-as-a-judge implementation using DeepEval G-Eval with Usefulness and Faithfulness metrics. |
| `tests/evals/eval_skeptic.py` | Reference-based evaluation reporting confusion matrix, accuracy, precision, recall, and scope drift. |
| `tests/evals/eval_verifier.py` | Evaluates bad items caught, false rejections, and prompt injection defense. |
| `tests/evals/eval_analyst.py` | Measures verdict classification accuracy and reference-free G-Eval Usefulness. |
| `tests/evals/eval_editor.py` | Evaluates editorial rule compliance on real Analyst output and G-Eval Faithfulness per brief. |
| `tests/evals/eval_pipeline.py` | End-to-end evaluation on 12 frozen inputs tracking leakage, gate verdict, latency, and calls. |
| `tests/evals/eval_history.py` | Online/offline consistency evaluation comparing production history before and after 2026-09-04. |
| `tests/evals/run_evals.py` | Master evaluation suite runner printing a single plain table and tracking regressions. |
| `frontend/src/components/AgentEvaluations.jsx` | Minimal React component (~85 lines) displaying live evaluation scorecards from `/eval_results.json`. |

---

## 3. The Evaluation Suite

### `eval_skeptic.py`
- **What it measures**: Classification accuracy, precision, recall, and scope drift (filtering enterprise/finance noise).
- **How it works**: Passes 25 golden signals through `deduplicate_and_filter_node` in chunks of 5 and builds a 2x2 confusion matrix against ground-truth labels.
- **Three-Sentence Interview Answer**: "We evaluate the Skeptic agent on 25 benchmark signals to measure how it separates practical open-source tools from enterprise noise. Using a confusion matrix, we track precision, recall, and scope drift to evaluate how corporate finance and duplicate patch releases are filtered out early. On 25 golden signals it scored 16/25 = 64% (with this few cases, roughly 45-80%) accuracy against an always-KEEP baseline of 18/25 = 72% (with this few cases, roughly 52-86%), and it rejected 6/7 = 86% (with this few cases, roughly 49-97%) of the items that should be rejected, so the filter is only partly effective."

### `eval_verifier.py`
- **What it measures**: Groundedness, anti-hype verification, false rejection of valid tools, and prompt injection defense.
- **How it works**: Evaluates 22 valid golden tools and 16 bad items (exaggerations, wrong versions, empty evidence, and 5 prompt injections) through `verifier_node`.
- **Three-Sentence Interview Answer**: "Our Verifier evaluation tests whether the agent fact-checks claims against scraped evidence without hallucinating or succumbing to prompt injections. We evaluate 38 cases comprising genuine tools, subtle numerical alterations, and adversarial prompt injections embedded in README files or XML tags. It caught 14/16 = 88% (with this few cases, roughly 64-97%) of the bad items, wrongly rejected 5/22 = 23% (with this few cases, roughly 10-43%) of the good ones, and 2/5 = 40% of 5 prompt-injection attempts succeeded, so the defence is partial."

### `eval_analyst.py`
- **What it measures**: Actionable developer verdict accuracy and reference-free usefulness scoring on 15 golden cases.
- **How it works**: Compares model verdicts against expected labels (WATCH, INTEGRATE, READ) and uses DeepEval G-Eval to score practical pedagogical utility.
- **Three-Sentence Interview Answer**: "The Analyst evaluation combines reference-based verdict matching with reference-free G-Eval LLM-as-a-judge scoring across 15 golden cases. It validates that the model correctly classifies tools into actionable verdicts (achieving 13/15 = 87% (with this few cases, roughly 62-96%)) while scoring developer usefulness. Average G-Eval usefulness was 0.49. We explicitly flag in our reports that the LLM judge is uncalibrated to maintain scientific rigor."

### `eval_editor.py`
- **What it measures**: Adherence to strict editorial formatting constraints and reference-free factual faithfulness per brief.
- **How it works**: Feeds real Analyst outputs to the Editor, executes automated quality rule checks (bold lead, no TL;DR, unique categories), and evaluates DeepEval G-Eval Faithfulness.
- **Three-Sentence Interview Answer**: "Our Editor evaluation checks whether final publication briefs comply with strict editorial guidelines while faithfully representing the underlying technical evidence. It runs rule-based assertions to verify bold lead-in sentences, forbidden labels, and category uniqueness, followed by a G-Eval Faithfulness check. Grounded numbers passed on 5/5 = 100% (with this few cases, roughly 57-100%) of briefs, and the average G-Eval faithfulness was 0.96."

### `eval_pipeline.py`
- **What it measures**: End-to-end multi-agent pipeline robustness, leakage prevention, latency, and quality gate publication decisions on 12 frozen inputs.
- **How it works**: Feeds 6 good signals, 3 should-reject signals, and 3 planted bad signals through the complete agent chain without external network calls.
- **Three-Sentence Interview Answer**: "The pipeline evaluation tests our complete multi-agent system on frozen benchmark inputs to measure end-to-end leakage, operational latency, and quality gate decisions. In the run, 0 of 6 bad inputs reached the final briefs, the gate decision was WOULD PUBLISH, and average faithfulness was 0.0. This demonstrates how the components perform together under frozen inputs."

### `eval_history.py`
- **What it measures**: Online vs. offline consistency by evaluating published production history before and after major pipeline changes.
- **How it works**: Runs the same deterministic rule checks across `data/history.json` before and after 2026-09-04.
- **Three-Sentence Interview Answer**: "Our history evaluation bridges offline benchmark testing with real-world production data across 41 days of published archives. By running our deterministic quality checks over historical briefs, it shows the output degrading after September 4th: the bold-lead rule passed on 23 of 23 days before and 7 of 18 days after. The cause, HTTP 429 rate limits, came from the GitHub Actions logs, not from this check."

---

## 4. How the Quality Gate Works

The Quality Gate in `backend/run_agent.py` is the final safety barrier before content is published or emailed.

1. **Trigger Condition**: Executes immediately after the Editor node returns final briefs.
2. **Blocking Checks**:
   - **Hard Failures**: If any node recorded a fallback (`health.has_fallbacks`), publication is blocked.
   - **Candidate Volume**: If fewer than `MIN_BRIEFS = 3` briefs survived, publication is blocked unless it was a genuine quiet day (zero candidates survived from the start and zero LLM errors occurred).
   - **Quality Rule Violations**: Briefs are evaluated using `validate_briefs` in `backend/app/checks.py`. Items failing checks are dropped.
3. **Outcomes**:
   - **Blocked**: Exits with code 1, writes an audit record to `data/runs/DATE.degraded.json`. History, archives, and subscriber email dispatches are left untouched.
   - **Published**: Enforces at most 5 items and category uniqueness, writes `data/runs/DATE.json`, appends briefs to `data/history.json`, updates markdown archives, and triggers email notifications.

---

## 5. Glossary of Evaluation Terms

- **Precision**: The proportion of items flagged as relevant/positive that were truly positive: $TP / (TP + FP)$. High precision means few false alarms.
- **Recall**: The proportion of actual positive items that were successfully identified: $TP / (TP + FN)$. High recall means few missed opportunities.
- **G-Eval**: A framework developed by DeepEval using frontier LLMs to evaluate generative outputs against natural language rubrics, assigning continuous scores with chain-of-thought justifications.
- **Reference-Based Evaluation**: Comparing model outputs directly against ground-truth labels (e.g., matching a verdict against `INTEGRATE`).
- **Reference-Free Evaluation**: Evaluating the quality of model outputs using criteria rubrics (e.g., judging faithfulness against evidence) without needing a human reference answer.
- **Regression Testing**: Re-running benchmarks across code changes to detect whether previously passing cases began failing.
- **Fail-Closed Architecture**: A safety-first system design where any unexpected failure or corrupted state causes the system to halt safely rather than publishing unverified or fallback content.
- **Wilson Score Interval**: A binomial proportion confidence interval that provides realistic accuracy bounds even on small sample sizes ($N < 50$), avoiding overly optimistic percentage estimates.

---

## 6. Ten Key AI Engineering Interview Questions

### Q1: Why did you build DailyDiff with LangGraph instead of a simple linear Python script?
**Answer**: "LangGraph provides stateful cyclic graph execution with strict schema validation across node transitions. It allows each agent to operate on an explicit `AgentState`, enabling isolated node execution, granular error recovery, and clean unit testing. In production, this architecture allows us to fail closed at specific graph boundaries while tracking runtime telemetry per node."

### Q2: Why do Verifier, Analyst, and Editor make one batched LLM call instead of individual calls per candidate?
**Answer**: "Batching candidates into a single prompt reduces LLM calls from up to 22 per run to 4 (one each for Skeptic, Verifier, Analyst and Editor). On 2026-09-28 a degraded run took 1 h 53 min because of repeated 429 retries; the production run on 2026-10-14 spent about 144 seconds in LLM calls (skeptic 27 s, verifier 16 s, analyst 14 s, editor 87 s), and the frozen-input pipeline eval took 4.16 seconds with 2 calls. Furthermore, batching allows the Editor to observe all candidates simultaneously to enforce global constraints like category uniqueness."

### Q3: What does it mean that your pipeline 'fails closed'?
**Answer**: "Failing closed means that if an API fails, times out, or returns invalid JSON after one retry, the pipeline halts and refuses to publish. Many LLM systems fail open by silently substituting generic fallback text or hardcoded templates, which degrades content quality. DailyDiff records the failure in an audit snapshot, blocks publication at the gate, and exits with code 1."

### Q4: How do you protect your pipeline from prompt injections embedded inside crawled GitHub READMEs?
**Answer**: "We employ defense-in-depth: all untrusted text from crawled web pages and repository READMEs is XML-escaped (`<` and `>` replaced with HTML entities) and wrapped in explicit delimiter tags. Our prompts instruct the model to treat content within delimiter tags solely as reference data. In our evaluations, 2/5 = 40% of 5 attempts still succeeded, demonstrating that prompt escaping alone is only a partial defense against sophisticated adversarial injections."

### Q5: Why did you choose DeepEval G-Eval over basic embedding similarity or BLEU/ROUGE scores?
**Answer**: "BLEU and ROUGE measure n-gram overlap against a reference text, which fails for generative summarization where phrasing varies. Embedding similarity measures topical proximity but cannot detect subtle factual hallucinations or tone violations. DeepEval G-Eval uses chain-of-thought criteria evaluation to inspect whether claims are strictly grounded in reference documentation."

### Q6: Why do you use Wilson score intervals when reporting evaluation metrics?
**Answer**: "On small test suites ($N=25$ or $N=15$), reporting a flat percentage like '80%' can be misleading because the sample size is small. The Wilson score interval calculates a statistically sound confidence interval (e.g., 61%–91% at 95% confidence). This communicates statistical uncertainty honestly, which is critical when evaluating models with limited labeled data."

### Q7: How does your quality gate prevent publishing hallucinated statistics or version numbers?
**Answer**: "We use a deterministic regex check in `checks.py` that extracts numeric tokens—such as versions (`v2.4`), multipliers (`10x`), percentages (`40%`), and counts (`250k`)—from the generated brief and verifies their presence in the scraped evidence text. If the LLM invents a benchmark metric or alters a version number, the brief fails validation and is rejected by the gate."

### Q8: What was the root cause of the production degradation on 2026-09-04, and how did you fix it?
**Answer**: "On September 4th, API rate limits (HTTP 429) caused individual node calls to fail after minutes of retrying. Because nodes silently caught errors and returned generic fallback text, degraded editions with exactly 3 briefs and missing summaries were published. We resolved this by batching calls, implementing multi-provider fallbacks with short timeouts, eliminating silent fallbacks, and adding a strict quality gate that blocks publication on degraded runs."

### Q9: Why did you keep the LLM judge uncalibrated, and how would you calibrate it in a real production environment?
**Answer**: "Our LLM judge uses zero-shot criteria prompts without few-shot anchoring against human gold-standard ratings, so its scores represent raw model assessments. In production, we would calibrate the judge by having human domain experts score a validation set, calculating Cohen's Kappa to measure human-model agreement, and tuning evaluation criteria and few-shot examples until the agreement is good enough for the use case."

### Q10: How do you ensure evaluations remain trustworthy without fake or fallback numbers?
**Answer**: "Every metric in our evaluation scorecard is computed directly from live model responses on real test cases. We eliminated all mock bypasses (`FAST_EVAL`), synthetic baselines, and catch-all ground-truth fallbacks. If an API call fails or times out, the case is recorded as an ERROR and the run exits with code 1 rather than reporting a fabricated pass."
