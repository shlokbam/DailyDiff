# Codebase Inventory

Temporary inventory file created during Phase 0 to guide simplification and evaluation redesign.
Evaluated against Rule R2: "Would an interviewer ask about this, and can a beginner explain it in two minutes?"

| File | Line Count | Action | Reason |
| :--- | :--- | :--- | :--- |
| **`backend/run_agent.py`** | 352 | **SIMPLIFY** | Core pipeline execution & publish gate. Strip second budget & warn mode; target <200 lines. |
| **`backend/test_api.py`** | 69 | **KEEP** | Standard unit tests for FastAPI status and subscribe/unsubscribe endpoints. |
| **`backend/requirements.txt`** | 17 | **KEEP** | Core Python dependencies. |
| **`backend/app/__init__.py`** | 11 | **KEEP** | Package initializer. |
| **`backend/app/config.py`** | 50 | **SIMPLIFY** | Application paths and environment variables; retain only settings needed by pipeline and API. |
| **`backend/app/checks.py`** | 233 | **SIMPLIFY** | Quality rule validation. Condense into plain functions; target <120 lines. |
| **`backend/app/database.py`** | 358 | **SIMPLIFY** | Strip all DB evaluation tables and persistence functions; retain only subscription storage. |
| **`backend/app/email_dispatcher.py`** | 328 | **KEEP** | Protected by Rule R6: Do not touch email dispatcher. |
| **`backend/app/main.py`** | 247 | **SIMPLIFY** | Strip `/api/evals/*` endpoints; retain status, subscription, and history endpoints. |
| **`backend/app/run_health.py`** | 148 | **SIMPLIFY** | Retain only tracking fields read by gate, snapshot, or evals; target <70 lines. |
| **`backend/app/schemas.py`** | 23 | **SIMPLIFY** | Strip evaluation schemas; retain subscription request/response models. |
| **`backend/app/agents/__init__.py`** | 1 | **KEEP** | Package initializer. |
| **`backend/app/agents/graph.py`** | 36 | **KEEP** | Defines the 6-node LangGraph execution flow. |
| **`backend/app/agents/state.py`** | 24 | **KEEP** | TypedDict defining graph state schema. |
| **`backend/app/agents/models.py`** | 183 | **SIMPLIFY** | Provider fallback chain Groq -> Gemini -> Mistral with 30s timeout and 1 JSON retry; target <100 lines. |
| **`backend/app/agents/scout.py`** | 312 | **SIMPLIFY** | Keep Atom/RSS parsing, redirects, null body safety; remove confidence scores. |
| **`backend/app/agents/skeptic.py`** | 187 | **SIMPLIFY** | Fail-closed signal filter with clear prompt; target <130 lines. |
| **`backend/app/agents/researcher.py`** | 106 | **SIMPLIFY** | Standardized evidence extraction; target <130 lines. |
| **`backend/app/agents/verifier.py`** | 138 | **SIMPLIFY** | Single batched call, drops missing evidence, escapes tags; target <130 lines. |
| **`backend/app/agents/analyst.py`** | 170 | **SIMPLIFY** | Single batched call, drops bad items with soft warning; target <130 lines. |
| **`backend/app/agents/editor.py`** | 196 | **SIMPLIFY** | Single batched call, formats bold lead & designated categories; target <130 lines. |
| **`scripts/purge_fake_eval_runs.py`** | 122 | **DELETE** | Obsolete cleanup script for deleted database evaluation tables. |
| **`tests/conftest.py`** | 8 | **KEEP** | Pytest root configuration and test setup. |
| **`tests/test_checks.py`** | 64 | **SIMPLIFY** | Primary test file 1 of 5: verify each rule check with good and bad examples. |
| **`tests/test_gate.py`** | 230 | **SIMPLIFY** | Primary test file 2 of 5: verify publish gate blocking, quiet day, and minimum briefs. |
| **`tests/test_scout_parsing.py`** | 52 | **KEEP** | Primary test file 3 of 5: verify Atom/RSS feed ingestion and null bodies. |
| **`tests/test_no_fake_results.py`** | 60 | **KEEP** | Primary test file 4 of 5: guard against FAST_EVAL, simulated scores, and fake baselines. |
| **`tests/test_nodes.py`** | NEW | **SIMPLIFY** | Primary test file 5 of 5: verify node behaviors (fail-closed, 1 retry, missing evidence, prompt escape). |
| **`tests/test_adversarial_e3.py`** | 58 | **DELETE** | Replaced by clean tests in Phase 2/3. |
| **`tests/test_checks_d5.py`** | 71 | **DELETE** | Useful assertions merged into `test_checks.py`. |
| **`tests/test_decisions_d8.py`** | 67 | **DELETE** | Useful assertions merged into `test_gate.py` and `test_nodes.py`. |
| **`tests/test_editor_d6.py`** | 89 | **DELETE** | Useful assertions merged into `test_nodes.py`. |
| **`tests/test_escape_untrusted_d7.py`** | 60 | **DELETE** | Useful assertions merged into `test_nodes.py`. |
| **`tests/test_eval_pipeline_d1.py`** | 52 | **DELETE** | Useful assertions merged into `test_nodes.py`. |
| **`tests/test_evidence_window_d4.py`** | 33 | **DELETE** | Useful assertions merged into `test_checks.py`. |
| **`tests/test_gate_d2.py`** | 205 | **DELETE** | Useful assertions merged into `test_gate.py`. |
| **`tests/test_history_baseline_e4.py`** | 49 | **DELETE** | Replaced by `eval_history.py`. |
| **`tests/test_labeling_tools_e2.py`** | 135 | **DELETE** | Labeling tool tests deleted with obsolete labeling tools. |
| **`tests/test_metrics_e1.py`** | 74 | **DELETE** | Overly complex statistical metrics deleted. |
| **`tests/test_models_retry_d3.py`** | 54 | **DELETE** | Useful assertions merged into `test_nodes.py`. |
| **`tests/test_runner_robustness_d11.py`** | 42 | **DELETE** | Useful assertions merged into `test_gate.py`. |
| **`tests/test_smoke_in_process_d10.py`** | 21 | **DELETE** | Obsolete smoke evaluation test. |
| **`tests/fixtures/runs/2026-10-12.json`** | 53 | **DELETE** | Obsolete test fixture. |
| **`tests/fixtures/runs/2026-10-13.degraded.json`** | 15 | **DELETE** | Obsolete test fixture. |
| **`tests/fixtures/runs/2026-10-13.json`** | 47 | **DELETE** | Obsolete test fixture. |
| **`tests/evals/golden_dataset.json`** | 790 | **KEEP** | Core benchmark dataset across 4 nodes (25 signals). Kept immutable. |
| **`tests/evals/adversarial_cases.json`** | 4424 | **DELETE** | 4k-line synthetic generated file; replaced by 13 hand-written `planted_errors.json`. |
| **`tests/evals/make_adversarial.py`** | 378 | **DELETE** | Synthetic adversarial generator; not needed for interview prep. |
| **`tests/evals/export_labeling_sheet.py`** | 300 | **DELETE** | Production-scale annotation sheet generator; fails R2. |
| **`tests/evals/import_labels.py`** | 266 | **DELETE** | Annotation ingestion script; fails R2. |
| **`tests/evals/relabel_check.py`** | 85 | **DELETE** | Inter-annotator agreement utility; fails R2. |
| **`tests/evals/dataset_stats.py`** | 145 | **DELETE** | Complex dataset analysis tool; fails R2. |
| **`tests/evals/metrics.py`** | 235 | **DELETE** | Over-engineered metrics module; replaced by ~10 line Wilson interval in `common.py`. |
| **`tests/evals/eval_published_history.py`** | 242 | **DELETE** | Replaced by concise `eval_history.py` (<40 lines). |
| **`tests/evals/baselines/history_checks.json`** | 950 | **DELETE** | Obsolete baseline artifact. |
| **`tests/evals/live_outputs.py`** | 375 | **DELETE** | Caching and stale eval output layer; replaced by direct execution. |
| **`tests/evals/deepeval_adapter.py`** | 156 | **DELETE** | Convoluted DeepEval adapter; consolidated into concise `judge.py`. |
| **`tests/evals/deepeval_metrics.py`** | 75 | **DELETE** | Consolidated into concise `judge.py`. |
| **`tests/evals/deepeval_judge.py`** | 90 | **DELETE** | Consolidated into concise `judge.py`. |
| **`tests/evals/run_meta.py`** | 165 | **DELETE** | Complex run metadata logger; fails R2. |
| **`tests/evals/smoke_model.py`** | 140 | **DELETE** | Smoke testing model calls; fails R2. |
| **`tests/evals/run_all_evals.py`** | 193 | **DELETE** | Replaced by streamlined `run_evals.py`. |
| **`tests/evals/test_deepeval_nodes.py`** | 76 | **DELETE** | Redundant pytest wrapper for evals; fails R2. |
| **`tests/evals/README.md`** | 105 | **DELETE** | Obsolete evals README; evals documented in main README & EXPLAIN.md. |
| **`tests/evals/smoke_results.json`** | 929 | **DELETE** | Stale smoke run outputs. |
| **`tests/evals/.cache/*`** | 170 | **DELETE** | Stale eval caches and labeling keys. |
| **`tests/evals/eval_skeptic.py`** | 181 | **SIMPLIFY** | Streamlined reference-based eval on 25 golden cases. |
| **`tests/evals/eval_verifier.py`** | 178 | **SIMPLIFY** | Streamlined reference-based eval with planted_errors.json. |
| **`tests/evals/eval_analyst.py`** | 218 | **SIMPLIFY** | Streamlined verdict match + G-Eval Usefulness eval. |
| **`tests/evals/eval_editor.py`** | 184 | **SIMPLIFY** | Streamlined rule checks + G-Eval Faithfulness on real Analyst output. |
