# Retry & Resume Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Failed runs are retried at 11:00 and 13:00 IST, resuming from the failed step (or restarting from Scout with rejected items skipped), and a failed subscriber email is retried by later runs.

**Architecture:** A per-day JSON state file (`data/runs/state/YYYY-MM-DD.json`) records each graph step's status and output. `run_agent.py` streams the LangGraph graph step by step, applies the stage rules after each step, saves state, and stops on the first failure. Later cron runs load the file and build the graph starting at the first unfinished step. Email delivery status lives in the same file.

**Tech Stack:** Python 3.12, LangGraph 0.1.4 (`graph.stream`, default update chunks `{node_name: update}`), httpx, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-26-retry-and-resume-design.md`

## Global Constraints

- Cron (Mon/Wed/Fri, UTC): `30 3 * * 1,3,5`, `30 5 * * 1,3,5`, `30 7 * * 1,3,5`.
- State file path: `data/runs/state/YYYY-MM-DD.json`; one per UTC date.
- Stage names = graph node names, in order: `scout`, `skeptic`, `research`, `verify`, `analyze`, `editor`.
- Minimum briefs: existing `MIN_BRIEFS` env var, default `3`.
- Backend wake: `GET {BACKEND_API_URL}/api/status` every 10s, up to 120s; only HTTP 200 counts as success for status and for `POST /api/notify-subscribers`.
- Email status values: `not_started`, `pending`, `sent`, `skipped`.
- Offline tests only (`PYTHONPATH=backend pytest tests -m "not live" -q`); no live HTTP or LLM calls.
- `check_briefs(...)` keeps its current signature (used by `tests/evals/eval_pipeline.py`).

## Review Focus

- **Restart from Scout finds nothing new:** after a weak fact-check, if every fresh signal is published or in `rejected_urls`, the Skeptic passes 0 and today's code would publish an empty "quiet day" edition. Expected: on a restart (`rejected_urls` non-empty), Verifier approving fewer than `MIN_BRIEFS` is a failure even with 0 input → nothing published, next run restarts again. Test in Task 4.
- **Corrupt or half-written state file:** a crash mid-write must not wedge every later run. Expected: saves are atomic (temp file + rename); an unreadable file logs a warning and starts fresh. Test in Task 1.
- **Yesterday's state file still on disk:** a new date must start fresh. Expected: only `<today>.json` is read. Test in Task 1.
- **Published before this feature existed (history entry, no state file):** Expected: treated as done, exit 0, no email resent. Test in Task 5.
- **Backend never wakes:** Expected: give up after the wake timeout, email stays `pending`, `attempts` incremented, exit 1, history untouched. Test in Task 5.

---

### Task 1: Daily state file module

**Files:**
- Create: `backend/app/run_state.py`
- Test: `tests/test_run_state.py`

**Interfaces:**
- Produces:
  - `STAGES: list[str] = ["scout", "skeptic", "research", "verify", "analyze", "editor"]`
  - `new_state(date_str: str) -> dict` — `{"date", "stages": {}, "rejected_urls": [], "email": {"status": "not_started", "attempts": 0, "last_error": None}, "attempts": []}`
  - `load_state(state_dir: Path, date_str: str) -> dict` — reads `state_dir/f"{date_str}.json"`; missing or invalid JSON → `new_state` (log warning on invalid).
  - `save_state(state_dir: Path, state: dict) -> None` — creates dir, writes `<date>.json.tmp` then `os.replace`.
  - `mark_done(state, stage: str, output: dict) -> None`, `mark_failed(state, stage: str, reason: str) -> None`
  - `first_unfinished_stage(state) -> str | None` — first stage in `STAGES` whose status is not `"done"`.
  - `merged_outputs(state) -> dict` — dict-merge of `output` of done stages in `STAGES` order (later stages overwrite, so `analyze`'s `vetted_candidates` wins over `verify`'s).
  - `reset_stages(state) -> None` — `stages = {}`; keeps `rejected_urls`, `email`, `attempts`.
  - `add_rejected_urls(state, urls: Iterable[str]) -> None` — appends unseen URLs, preserving order.
  - `record_attempt(state, git_sha: str, failed_stage: str | None, reason: str | None) -> None` — appends `{"started_at": utc iso, "git_sha", "failed_stage", "reason"}`.

- [ ] **Step 1: Write failing tests** in `tests/test_run_state.py` (use `tmp_path`):
  - `test_load_missing_returns_new_state`: `load_state(tmp_path, "2026-10-21") == new_state("2026-10-21")`.
  - `test_save_then_load_roundtrip`: mark `scout` done with `{"raw_signals": [{"url": "https://a"}]}`, save, load → equal; no `*.tmp` file left in `tmp_path`.
  - `test_corrupt_file_starts_fresh`: write `"{not json"` to `2026-10-21.json` → `load_state` returns `new_state`.
  - `test_other_date_ignored`: save state for `2026-10-19` → `load_state(tmp_path, "2026-10-21")["stages"] == {}`.
  - `test_first_unfinished_stage`: none done → `"scout"`; scout..analyze done, editor failed → `"editor"`; all six done → `None`.
  - `test_merged_outputs_later_stage_wins`: verify output `{"vetted_candidates": [1]}`, analyze `{"vetted_candidates": [2]}` → merged `["vetted_candidates"] == [2]`; failed stages contribute nothing.
  - `test_reset_keeps_rejected_email_attempts`: after `add_rejected_urls`, setting email status, `record_attempt`, and `reset_stages` → `stages == {}`, other three keys unchanged.
  - `test_add_rejected_urls_dedupes`: add `["a", "b"]` then `["b", "c"]` → `["a", "b", "c"]`.

- [ ] **Step 2: Run** `PYTHONPATH=backend pytest tests/test_run_state.py -v` — Expected: FAIL (`ModuleNotFoundError: app.run_state`).

- [ ] **Step 3: Implement** `backend/app/run_state.py` with the interfaces above. Stdlib only (`json`, `os`, `logging`, `datetime`, `pathlib`); match the short-docstring style of `run_health.py`.

- [ ] **Step 4: Run** the same command — Expected: 8 passed.

- [ ] **Step 5: Commit** `git add backend/app/run_state.py tests/test_run_state.py && git commit -m "feat(pipeline): add daily run state file"`

---

### Task 2: Graph can start at any step

**Files:**
- Modify: `backend/app/agents/graph.py:13-36`
- Test: `tests/test_resume.py` (new)

**Interfaces:**
- Consumes: `STAGES` from `app.run_state`.
- Produces: `create_agent_graph(start_at: str = "scout")` — adds only the nodes from `start_at` onward (in `STAGES` order), entry point `start_at`, linear edges, last → `END`. Unknown `start_at` → `ValueError`.

- [ ] **Step 1: Write failing tests** in `tests/test_resume.py`:
  - `test_graph_starts_at_editor_runs_only_editor`: patch `app.agents.graph.editor_node` to a function returning `{"final_briefs": ["x"]}` and the other five node functions to `MagicMock(side_effect=AssertionError)`; `create_agent_graph("editor").invoke({...empty AgentState keys...})["final_briefs"] == ["x"]`.
  - `test_graph_default_still_starts_at_scout`: with all six patched to record their name into a list, `invoke` runs them in `STAGES` order.
  - `test_graph_unknown_start_raises`: `pytest.raises(ValueError)` for `"nope"`.

- [ ] **Step 2: Run** `PYTHONPATH=backend pytest tests/test_resume.py -v` — Expected: FAIL (`create_agent_graph() takes 0 positional arguments`).

- [ ] **Step 3: Implement** the new `create_agent_graph(start_at="scout")`. Map stage name → node function with a dict, iterate `STAGES[STAGES.index(start_at):]`. Node functions must be looked up at call time from module globals so the test patches apply.

- [ ] **Step 4: Run** the same command — Expected: 3 passed. Also run `PYTHONPATH=backend pytest tests -m "not live" -q` — Expected: all pass.

- [ ] **Step 5: Commit** `git commit -am "feat(graph): allow starting the pipeline at any stage"` (add `tests/test_resume.py`).

---

### Task 3: Skeptic skips today's rejected URLs

**Files:**
- Modify: `backend/app/agents/state.py` (add field), `backend/app/agents/skeptic.py:36-45`
- Test: `tests/test_nodes.py` (append)

**Interfaces:**
- Produces: `AgentState.exclude_urls: List[str]`. The Skeptic drops any raw signal whose URL, normalised as `url.strip().rstrip("/").lower()` (same as `get_published_urls`), is in published URLs **or** `state.get("exclude_urls", [])`.

- [ ] **Step 1: Write failing test** `test_skeptic_drops_excluded_urls`: raw signals with URLs `https://github.com/a/b/` and `https://github.com/c/d`; state `exclude_urls=["https://GitHub.com/a/b"]`; patch `get_published_urls` → `set()`, `extract_history_summary` → `"none"`, and `get_llm` → a `MagicMock` whose `invoke` returns `AIMessage(content="[0]")`. Assert result candidates' URLs == `["https://github.com/c/d"]` and `health.counts["after_dedup"] == 1`.

- [ ] **Step 2: Run** `PYTHONPATH=backend pytest tests/test_nodes.py::test_skeptic_drops_excluded_urls -v` — Expected: FAIL (candidate is `a/b`).

- [ ] **Step 3: Implement** the field and the extra exclusion in `deduplicate_and_filter_node`.

- [ ] **Step 4: Run** `PYTHONPATH=backend pytest tests -m "not live" -q` — Expected: all pass.

- [ ] **Step 5: Commit** `git commit -am "feat(skeptic): skip URLs rejected earlier the same day"`

---

### Task 4: Runner streams, saves per step, applies stage rules, resumes

**Files:**
- Modify: `backend/run_agent.py` (`main`, `publish_gate`; keep `check_briefs` unchanged)
- Modify: `tests/test_gate.py` (mocks use `stream` instead of `invoke`)
- Test: `tests/test_resume.py` (append)

**Interfaces:**
- Consumes: Task 1 functions; `create_agent_graph(start_at)` from Task 2; `exclude_urls` from Task 3.
- Produces:
  - `HEALTH_NODE = {"skeptic": "skeptic", "verify": "verifier", "analyze": "analyst", "editor": "editor"}` (graph stage → name used in `health.mark_fallback`).
  - `stage_failure(stage: str, before: dict, update: dict, min_briefs: int, is_restart: bool) -> tuple[str | None, bool]` — returns `(reason, restart_from_scout)`:
    - a `health.fallbacks` entry whose `node == HEALTH_NODE.get(stage)` → `(its reason, False)`;
    - `verify`: `n_in = len(before["researched_candidates"])`, `n_ok = len(update["vetted_candidates"])`; if `(n_in > 0 or is_restart) and n_ok < min_briefs` → `(f"Verifier approved {n_ok} of {n_in} candidates (minimum {min_briefs})", True)`;
    - `analyze`: if `len(before["vetted_candidates"]) > 0 and len(update["vetted_candidates"]) < min_briefs` → `(f"Analyst kept {n} candidates (minimum {min_briefs})", False)`;
    - otherwise `(None, False)`.
  - `run_pipeline(run_state: dict, state_dir: Path, min_briefs: int, git_sha: str) -> dict | None` — returns the final graph state, or `None` after recording a failure (state saved either way).
- `main()` behaviour after this task: `state_dir = DATA_DIR / "runs" / "state"`; load state; `run_pipeline`; on `None` → write `DATE.degraded.json` (existing `build_run_snapshot`) and `sys.exit(1)`; otherwise gate. If `check_briefs` returns reasons → `mark_failed(state, "editor", "; ".join(reasons))`, `record_attempt`, save, degraded snapshot, exit 1 (as today).

`run_pipeline` algorithm (the part the signature doesn't determine):

```text
start = first_unfinished_stage(state)        # None only if a previous run crashed after editor; treat as "editor"
graph_input = empty AgentState keys | merged_outputs(state) | {"exclude_urls": state["rejected_urls"]}
current = dict(graph_input)
for chunk in create_agent_graph(start).stream(graph_input):
    for stage, update in chunk.items():
        reason, restart = stage_failure(stage, current, update, min_briefs, is_restart=bool(state["rejected_urls"]))
        if reason and restart:
            add_rejected_urls(state, [c["url"] for c in current["researched_candidates"]
                                      if c["url"] not in {v["url"] for v in update["vetted_candidates"]}])
            reset_stages(state); record_attempt(state, sha, stage, reason); save; return None
        if reason:
            mark_failed(state, stage, reason); record_attempt(...); save; return None
        mark_done(state, stage, update); save
        current.update(update)
return current
```

- [ ] **Step 1: Update `tests/test_gate.py`** — add helper `def _streaming_graph(final_state, before=None)` returning a `MagicMock` whose `stream` yields `{"editor": final_state}` (calling `before()` first if given). Replace each `mock_graph.invoke...` with it; `failing_invoke` becomes the `before` callback. No assertion changes.

- [ ] **Step 2: Write failing tests** in `tests/test_resume.py` (patch `run_agent.DATA_DIR`, `ARCHIVE_DIR`, `HISTORY_FILE_PATH`, `init_db`, `append_to_history` exactly as `test_gate.py` does; build fake graphs with `stream` yielding per-stage chunks):
  - `test_failure_stops_and_saves_progress`: stream yields scout, skeptic, research, verify, analyze updates, then `health.mark_fallback("editor", "429")` and an editor chunk → `SystemExit(1)`; state file has the first five `done` with outputs, `editor` `failed` with reason containing `"429"`; one attempt recorded.
  - `test_resume_starts_at_failed_stage`: pre-save a state with scout..analyze done (analyze output has 5 vetted candidates) and editor failed; patch `run_agent.create_agent_graph` with a `MagicMock` → assert it was called with `"editor"` and the `stream` input contains the saved `vetted_candidates`.
  - `test_weak_verify_restarts_from_scout_with_rejected_urls`: research update has 4 candidates (URLs u1..u4), verify update keeps only u1 → exit 1; saved state `stages == {}`, `rejected_urls == [u2, u3, u4]`; next `main()` call: `create_agent_graph` called with `"scout"` and stream input `exclude_urls == [u2, u3, u4]`.
  - `test_restart_with_nothing_new_is_not_a_quiet_day`: state has `rejected_urls=["u9"]`; stream yields skeptic/research/verify updates with empty lists → exit 1, `append_to_history` not called.
  - `test_analyst_too_few_reruns_analyst`: analyze update keeps 2 of 5 → `analyze` failed, `verify` still done; `first_unfinished_stage == "analyze"`.
  - `test_gate_rejection_marks_editor_failed`: full stream with editor producing 2 valid briefs → exit 1, `editor` failed.
  - `test_quiet_day_still_publishes`: fresh state, all updates empty, no fallbacks → `append_to_history` called with `[]`.

- [ ] **Step 3: Run** `PYTHONPATH=backend pytest tests/test_resume.py tests/test_gate.py -v` — Expected: new tests FAIL; updated gate tests FAIL (runner still calls `invoke`).

- [ ] **Step 4: Implement** `HEALTH_NODE`, `stage_failure`, `run_pipeline`, and the `main()` changes above. `publish_gate` stops calling `sys.exit` itself: it returns the `check_briefs` reasons, and `main` decides. Keep `build_run_snapshot`, `check_briefs`, archive and history writing unchanged. Leave the existing notify code in place for now (Task 5 replaces it).

- [ ] **Step 5: Run** `PYTHONPATH=backend pytest tests -m "not live" -q` — Expected: all pass.

- [ ] **Step 6: Commit** `git add backend/run_agent.py tests/test_gate.py tests/test_resume.py && git commit -m "feat(pipeline): save progress per stage and resume failed runs"`

---

### Task 5: Startup check and email wake / check / retry

**Files:**
- Modify: `backend/run_agent.py` (startup, replace notify block in `publish_gate`)
- Test: `tests/test_resume.py` (append)

**Interfaces:**
- Consumes: Task 1 state functions; `main()` from Task 4.
- Produces:
  - `todays_entry(history_path: Path, date_str: str) -> dict | None` — reads the JSON file directly (not `read_history`, so the test patch of `HISTORY_FILE_PATH` applies).
  - `send_notification(backend_url: str, token: str, entry: dict, poll_interval: float = 10, wake_timeout: float = 120) -> tuple[bool, str | None]` — polls `GET {backend_url}/api/status` until 200 or `wake_timeout`; then `POST {backend_url}/api/notify-subscribers` with `json={"date", "published_at", "briefs"}` from `entry`, header `X-Auth-Token`, timeout 60. Returns `(True, None)` only on 200; otherwise `(False, "<what failed>")`. Never raises.
  - `deliver_email(run_state: dict, state_dir: Path, entry: dict) -> bool` — if `BACKEND_API_URL` unset or `entry["briefs"]` empty → status `skipped`; else status `pending`, save, call `send_notification`; success → `sent`, failure → stays `pending`, `attempts += 1`, `last_error` set. Saves and returns `True` unless status ends `pending`.
- `main()` startup, before building any graph:
  - `entry = todays_entry(HISTORY_FILE_PATH, date_str)`; if found: email status `pending` → `deliver_email`, exit 0 if it returns True else exit 1; any other status (incl. `not_started` with no state file) → log "already done", return.
  - After a passing gate: write snapshot, history and archive as today, then `deliver_email(...)` with the new history entry; exit 1 if it returns False.

- [ ] **Step 1: Write failing tests** (patch `run_agent.httpx.get` / `run_agent.httpx.post` with `MagicMock`s; `poll_interval=0`):
  - `test_already_published_and_sent_exits_without_graph`: history has today, state email `sent` → `main()` returns; `create_agent_graph` not called; `httpx.post` not called.
  - `test_published_before_feature_exits_without_email`: history has today, no state file → same as above.
  - `test_pending_email_is_retried_only`: history has today, state email `pending` → `httpx.post` called once with `json["date"] == today`; `append_to_history` and `create_agent_graph` not called; state email `sent`.
  - `test_wake_polls_until_ready`: `httpx.get` returns status 503, 503, then 200; post returns 200 → `send_notification(...) == (True, None)`, `get.call_count == 3`.
  - `test_backend_never_wakes_stays_pending`: `httpx.get` always 503, `wake_timeout=0` → `(False, msg)`; through `main()` on a pending retry → `SystemExit(1)`, email `attempts` incremented, `last_error` set, `httpx.post` not called.
  - `test_notify_500_is_not_success`: get 200, post 500 → `(False, msg)` with `"500"` in msg.
  - `test_no_backend_url_marks_skipped`: `BACKEND_API_URL=""`, publishing run → email `skipped`, exit normally.

- [ ] **Step 2: Run** `PYTHONPATH=backend pytest tests/test_resume.py -v` — Expected: the 7 new tests FAIL.

- [ ] **Step 3: Implement** `todays_entry`, `send_notification`, `deliver_email`, and the `main()` changes. Remove the old fire-and-forget notify block. Use `time.sleep(poll_interval)` between polls; tests pass 0.

- [ ] **Step 4: Run** `PYTHONPATH=backend pytest tests -m "not live" -q` — Expected: all pass.

- [ ] **Step 5: Commit** `git commit -am "feat(pipeline): wake backend, verify notify response, retry pending email"`

---

### Task 6: Retry schedule and docs

**Files:**
- Modify: `.github/workflows/thrice_weekly_brief.yml:4-6`
- Modify: `README.md` (Reliability section, CI/CD table, Project Structure)

- [ ] **Step 1: Add crons** — the `schedule` list has exactly the three lines from Global Constraints. Leave `workflow_dispatch`, `concurrency`, and the `if: always()` commit step as they are.

- [ ] **Step 2: Verify** `python -c "import yaml,sys; d=yaml.safe_load(open('.github/workflows/thrice_weekly_brief.yml')); print([s['cron'] for s in d[True]['schedule']])"` prints the three cron strings. (PyYAML parses the `on` key as `True`.)

- [ ] **Step 3: Update README** — in Reliability, add a "Retries" bullet: 09:00/11:00/13:00 IST runs, resume from the failed step, Scout restart with rejected URLs skipped, email retry. Add the three crons to the CI/CD table. Add `runs/state/` to Project Structure, and `run_state.py` to the backend tree.

- [ ] **Step 4: Run** `PYTHONPATH=backend pytest tests -m "not live" -q` — Expected: all pass (this includes `test_no_fake_results.py`, which scans `.md`/`.yml`).

- [ ] **Step 5: Commit** `git commit -am "ci: add 11:00 and 13:00 IST retry runs; document retry and resume"`
