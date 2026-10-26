# Retry & Resume for Failed Runs — Design

**Date:** 2026-10-26
**Status:** Draft, awaiting review

## Problem

Subscribers get nothing on a day the pipeline fails, or when the edition publishes but the
email request to the backend fails.

- Most pipeline failures were temporary provider errors ("too many requests"). On 2026-10-21
  the Editor hit a 429 after Skeptic, Verifier and Analyst had already succeeded; waiting and
  trying again would have worked.
- `run_agent.py` posts to `/api/notify-subscribers` once, with no wake-up for Render's cold
  start, and never checks the response status — a 401/500 looks like success.

## Goal

Recover the same day without lowering the quality bar: an edition is sent only if it passes
the existing gate, and its email is retried until the backend accepts it.

**Success:**
- A run that fails for a temporary reason is published by a later retry the same day, without
  redoing steps that already succeeded.
- When the fact-checker approves too few items, the retry tries *different* items.
- A published edition whose email request failed is re-sent by the next run that day.

## 1. Run again later

- `.github/workflows/thrice_weekly_brief.yml` gets three schedules, Mon/Wed/Fri:
  `30 3`, `30 5`, `30 7` UTC (09:00, 11:00, 13:00 IST). The existing `concurrency: dailydiff`
  group keeps runs from overlapping.
- At startup, `run_agent.py` checks `data/history.json` for an entry with today's date:
  - found and email `sent` / `skipped` → log "already done", exit 0;
  - found and email `pending` → only retry the email (section 4), then exit;
  - not found → run or resume the pipeline.
- After the 13:00 run, nothing else happens that day.

## 2. Daily state file — don't redo finished work

- A new file per day: `data/runs/state/YYYY-MM-DD.json`. A new module,
  `backend/app/run_state.py`, loads and saves it.

  ```json
  {
    "date": "2026-10-21",
    "stages": {
      "scout":    {"status": "done",   "output": {"raw_signals": [...]}},
      "skeptic":  {"status": "done",   "output": {"candidates": [...]}},
      "research": {"status": "done",   "output": {"researched_candidates": [...]}},
      "verify":   {"status": "done",   "output": {"vetted_candidates": [...]}},
      "analyze":  {"status": "done",   "output": {"vetted_candidates": [...]}},
      "editor":   {"status": "failed", "reason": "Error code: 429 ..."}
    },
    "rejected_urls": [],
    "email": {"status": "not_started", "attempts": 0, "last_error": null},
    "attempts": [
      {"started_at": "...", "git_sha": "...", "failed_stage": "editor", "reason": "..."}
    ]
  }
  ```

- `run_agent.py` runs the graph with `graph.stream(...)` instead of `graph.invoke(...)`, so it
  sees each step as it finishes. After each step it applies the rules in section 3, saves the
  state, and stops the run as soon as a step fails (later steps are not started).
- `create_agent_graph()` takes an optional start step. On a retry, the graph is built with only
  that step and the ones after it (langgraph 0.1.4 refuses to compile a graph containing
  unreachable nodes — checked locally), and is given the saved outputs of earlier steps as its
  input state.
- The workflow already commits `data/` with `if: always()`, so a failed run's state is available
  to the next run. No new infrastructure.
- State is per date; a new run day always starts fresh.
- Unchanged: `data/runs/DATE.json` / `DATE.degraded.json`, history, archive.

## 3. When a step counts as done, and where a retry restarts

`MIN_BRIEFS` is the existing minimum (default 3).

| What happened | Step marked | Next run starts at |
|---|---|---|
| API or bad-JSON error in step X (`health` recorded a failure for X) | X `failed` | X |
| Verifier had candidates but approved fewer than `MIN_BRIEFS` | `verify` `failed` | **Scout**, skipping today's rejected items |
| Analyst left fewer than `MIN_BRIEFS` items | `analyze` `failed` | Analyst |
| Gate kept fewer than `MIN_BRIEFS` briefs | `editor` `failed` | Editor |
| Skeptic passed nothing, no errors (genuine quiet day) | all `done` | — publishes an empty edition, as today |

**Restarting from Scout after a weak fact-check:**
- Every URL the Skeptic passed that did not come out of the Verifier as VALID is added to
  `rejected_urls`. The list only grows during the day.
- All stage results are cleared; `rejected_urls`, `email` and `attempts` are kept.
- A new `AgentState` field, `exclude_urls`, carries `rejected_urls` into the graph. The Skeptic
  drops these URLs together with already-published ones, using the same URL normalisation.
- Scout fetches fresh signals (new items may have appeared), and the Skeptic picks from what is
  left, so the Verifier sees different candidates.
- On a restart (`rejected_urls` not empty), a Verifier result below `MIN_BRIEFS` is a failure
  even if it had nothing to check, so "nothing new left" never publishes an empty quiet-day
  edition.

These checks live in `run_agent.py` (it already owns `MIN_BRIEFS` and the gate); the agent nodes
themselves only change where noted in "Files touched".

## 4. Email — wake, check, retry later

- After the gate passes, the edition is written to history/archive exactly once, and
  `email.status` is set to `pending` (or `skipped` if `BACKEND_API_URL` is unset or the
  edition is empty). The state is saved before any network call.
- Sending:
  1. **Wake the backend:** `GET {BACKEND_API_URL}/api/status` every 10s, for up to 120s, until it
     answers 200 (covers Render's 30–50s cold start).
  2. **Send:** `POST /api/notify-subscribers` with today's edition from `history.json`.
  3. **Check:** only HTTP 200 counts. Then `email.status = "sent"`. Anything else (timeout,
     401, 500) → stays `pending`, with `attempts` incremented and `last_error` recorded.
- A run that ends with the email still `pending` exits 1, so the failure is visible in Actions.
- The 11:00 and 13:00 runs see the edition already published with email `pending` and only
  retry the email (steps 1–3). The pipeline is not re-run and the edition is not re-published.

## Example: 2026-10-21 under this design

| Run (IST) | What happens |
|---|---|
| 09:00 | Scout → Analyst done and saved. Editor gets 429 → `editor: failed`. Exit 1, no email. |
| 11:00 | Not published yet → starts at Editor with saved inputs (one LLM call). Gate passes → published. Backend wakes after ~40s → notify returns 200 → `email: sent`. |
| 13:00 | Published, email sent → exits 0. |

## Known limits (accepted for now)

- If none of the day's candidates pass the fact-check across all three runs, nothing is sent.
- `sent` means the backend *accepted* the request. The backend then sends in the background; a
  Brevo/SMTP failure there is not visible to the pipeline. Separate backend change.
- Retries starting at Verifier/Analyst/Editor reuse the first run's scraped evidence; only a
  restart from Scout re-scrapes.
- If the backend is down for all three runs, the edition is on the website but not emailed.

## Out of scope (possible later additions)

Code-level repair of failing briefs, an extra Editor attempt with feedback, honoring the
provider's "retry after N seconds", owner alerts, a second LLM provider, and backend-side
delivery tracking.

## Testing (offline, no live APIs)

- Today in history with email `sent` → `main()` exits 0 and never builds the graph.
- Today in history with email `pending` → only the notify path runs; graph never built; history
  not rewritten.
- Failure at step X → earlier steps `done` with outputs, X `failed`, later steps not run.
- Resume with `editor` failed → only the Editor node runs.
- Verifier approves fewer than 3 → `verify` failed, Skeptic-passed-but-not-VALID URLs added to
  `rejected_urls`; next run starts at Scout and the Skeptic excludes those URLs.
- Gate keeps fewer than 3 → `editor` failed.
- Email: backend answers 200 only after a few status polls → `sent`; notify returns 500 →
  `pending`, `attempts` incremented, exit 1. (HTTP mocked; polling interval patched to 0.)
- Existing gate tests (quiet day, hard failure, dropped brief, fewer than minimum) still pass.

## Files touched

| File | Change |
|---|---|
| `.github/workflows/thrice_weekly_brief.yml` | Two extra cron lines |
| `backend/app/run_state.py` | **New** — load/save daily state file |
| `backend/run_agent.py` | Startup check, stream + save per step, section 3 rules, resume, email wake/check/retry |
| `backend/app/agents/graph.py` | Optional start step |
| `backend/app/agents/state.py` | New `exclude_urls` field |
| `backend/app/agents/skeptic.py` | Also drop `exclude_urls` |
| `tests/test_resume.py` | **New** — tests above |
| `README.md` | Document retries, state file, and email retry |
