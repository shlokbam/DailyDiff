"""
DailyDiff Pipeline Runner & Publish Gate.
Orchestrates graph execution, quality gate validation, snapshot creation, and publication.
"""

import os
import sys
import json
import logging
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Tuple
import httpx

from app.config import DATA_DIR, ARCHIVE_DIR, HISTORY_FILE_PATH
from app.database import init_db, init_history_file, append_to_history
from app.run_health import health
from app.agents.graph import create_agent_graph
from app.agents.researcher import MAX_EVIDENCE_CHARS
from app.checks import validate_briefs, build_evidence
from app.agents.state import AgentState
from app.run_state import (
    load_state, save_state, mark_done, mark_failed, first_unfinished_stage,
    merged_outputs, reset_stages, add_rejected_urls, record_attempt,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("DailyDiff.runner")

# Backend wake-up before notifying subscribers (Render cold start takes 30-50s)
WAKE_TIMEOUT_SECONDS = 120
WAKE_POLL_SECONDS = 10

EMPTY_GRAPH_STATE = {"raw_signals": [], "candidates": [], "researched_candidates": [], "vetted_candidates": [], "final_briefs": []}

def get_git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
    except Exception:
        return "unknown"

def build_markdown_brief(briefs: list, date_str: str) -> str:
    lines = [f"# DailyDiff Brief — {date_str}\n"]
    for b in briefs:
        lines.append(f"### [{b.get('category')}] {b.get('title')}")
        lines.append(f"{b.get('description')}\n")
        lines.append(f"**Why it matters:** {b.get('why_it_matters')}\n")
        lines.append(f"**Who cares:** {b.get('who_cares')}\n")
        lines.append(f"**Verdict:** `{b.get('verdict')}` | [Source]({b.get('source_url')})\n\n---\n")
    return "\n".join(lines)

def build_run_snapshot(date_str: str, briefs: list, failure_reasons: list = None) -> dict:
    """Builds a small, informative snapshot of the run."""
    snapshot = {
        "date": date_str,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_sha": get_git_sha(),
        "counts": health.counts,
        "content_sources": health.content_sources,
        "models_used": health.models_used,
        "llm_calls": health.llm_calls_count,
        "durations_seconds": health.durations,
        "hard_failures": health.fallbacks,
        "warnings": health.warnings,
        "final_briefs": briefs,
    }
    if failure_reasons:
        snapshot["failure_reasons"] = failure_reasons
        snapshot["status"] = "degraded"
    else:
        snapshot["status"] = "healthy"
    return snapshot

def check_briefs(briefs, produced_count, candidate_urls, evidence_by_url, min_briefs):
    """Decides what may be published. No files, no exit. Returns (surviving_briefs, failure_reasons)."""
    surviving = []
    for b in briefs:
        errs = validate_briefs([b], evidence_by_url=evidence_by_url, candidate_urls=candidate_urls)
        if errs:
            logger.warning(f"Dropping brief '{b.get('title')}': {'; '.join(errs)}")
            health.add_warning(f"Dropped brief '{b.get('title')}': {errs[0]}")
        else:
            surviving.append(b)

    seen, unique = set(), []
    for b in surviving:
        if b.get("category") not in seen:
            seen.add(b.get("category"))
            unique.append(b)
    surviving = unique[:5]

    reasons = []
    if health.has_fallbacks:
        reasons.append(f"Hard node fallbacks: {health.fallbacks}")
    # A quiet day means the PIPELINE produced nothing and nothing failed. Briefs dropped by the gate do not count.
    quiet_day = produced_count == 0 and not health.has_fallbacks and health.llm_errors_count == 0
    if produced_count > 0 and not surviving:
        reasons.append(f"All {produced_count} briefs were dropped by the rule checks.")
    elif len(surviving) < min_briefs and not quiet_day:
        reasons.append(f"Produced {len(surviving)} briefs (minimum required: {min_briefs}).")
    return surviving, reasons

def publish_gate(briefs: list, candidate_urls: set, evidence_by_url: dict, date_str: str, runs_dir: Path, min_briefs: int, produced_count: int,
                 on_approved: Optional[Callable[[list], None]] = None) -> Tuple[list, list]:
    """Strict publish gate: drops invalid briefs, enforces categories.
    Returns (published_briefs, failure_reasons); nothing is published when there are reasons.
    on_approved(briefs) runs after approval, before anything is written."""
    briefs, failure_reasons = check_briefs(briefs, produced_count, candidate_urls, evidence_by_url, min_briefs)

    if failure_reasons:
        logger.error(f"[GATE REJECTION] Degraded run for {date_str}: {failure_reasons}")
        degraded_path = runs_dir / f"{date_str}.degraded.json"
        with open(degraded_path, "w") as f:
            json.dump(build_run_snapshot(date_str, briefs, failure_reasons), f, indent=2)
        return [], failure_reasons

    # 4. Gate passed: publish output
    logger.info(f"[GATE APPROVED] Publishing {len(briefs)} briefs for {date_str}...")
    if on_approved:
        on_approved(briefs)
    run_path = runs_dir / f"{date_str}.json"
    with open(run_path, "w") as f:
        json.dump(build_run_snapshot(date_str, briefs), f, indent=2)

    append_to_history(briefs, date_str)

    # Save Markdown archive
    parts = date_str.split("-")
    month_dir = ARCHIVE_DIR / parts[0] / parts[1]
    month_dir.mkdir(parents=True, exist_ok=True)
    with open(month_dir / f"{parts[2]}.md", "w") as f:
        f.write(build_markdown_brief(briefs, date_str))
    return briefs, []

# Graph stage -> node name used in health.mark_fallback
HEALTH_NODE = {"skeptic": "skeptic", "verify": "verifier", "analyze": "analyst", "editor": "editor"}

def stage_failure(stage: str, before: dict, update: dict, min_briefs: int, is_restart: bool) -> Tuple[Optional[str], bool]:
    """Decides whether a finished stage failed. Returns (reason, restart_from_scout)."""
    node = HEALTH_NODE.get(stage)
    for fb in health.fallbacks:
        if node and fb.get("node") == node:
            return fb.get("reason", "node failure"), False

    if stage == "verify":
        n_in = len(before.get("researched_candidates") or [])
        n_ok = len(update.get("vetted_candidates") or [])
        # A quiet day (nothing to check) is fine, except on a restart, where it means nothing new was found
        if (n_in > 0 or is_restart) and n_ok < min_briefs:
            return f"Verifier approved {n_ok} of {n_in} candidates (minimum {min_briefs})", True

    if stage == "analyze":
        n_in = len(before.get("vetted_candidates") or [])
        n_ok = len(update.get("vetted_candidates") or [])
        if n_in > 0 and n_ok < min_briefs:
            return f"Analyst kept {n_ok} candidates (minimum {min_briefs})", False

    return None, False

def run_pipeline(run_state: dict, state_dir: Path, min_briefs: int, git_sha: str) -> Optional[dict]:
    """Runs (or resumes) the graph one stage at a time, saving progress after each stage.
    Returns the final graph state, or None after recording a failure."""
    start = first_unfinished_stage(run_state) or "editor"  # all done but unpublished: redo the editor
    # Explicit flag: a restart can add no rejected URLs (e.g. 2 of 2 approved, below the minimum)
    is_restart = bool(run_state.get("restarted")) or bool(run_state["rejected_urls"])

    saved = {k: v for k, v in merged_outputs(run_state).items() if k in AgentState.__annotations__}
    graph_input = {**EMPTY_GRAPH_STATE, **saved, "exclude_urls": list(run_state["rejected_urls"])}
    current = dict(graph_input)

    logger.info(f"Executing DailyDiff graph workflow from stage '{start}'...")
    for chunk in create_agent_graph(start).stream(graph_input):
        for stage, update in chunk.items():
            update = update or {}
            reason, restart = stage_failure(stage, current, update, min_briefs, is_restart)
            if reason and restart:
                approved = {v.get("url") for v in update.get("vetted_candidates") or []}
                add_rejected_urls(run_state, [c.get("url") for c in current.get("researched_candidates") or [] if c.get("url") not in approved])
                reset_stages(run_state)
                run_state["restarted"] = True
                record_attempt(run_state, git_sha, stage, reason)
                save_state(state_dir, run_state)
                logger.error(f"[RESTART] {reason}. Next run restarts from scout, skipping {len(run_state['rejected_urls'])} rejected URLs.")
                return None
            if reason:
                mark_failed(run_state, stage, reason)
                record_attempt(run_state, git_sha, stage, reason)
                save_state(state_dir, run_state)
                logger.error(f"[STAGE FAILED] {stage}: {reason}. Next run resumes here.")
                return None
            mark_done(run_state, stage, update)
            save_state(state_dir, run_state)
            current.update(update)
    return current

def todays_entry(history_path: Path, date_str: str) -> Optional[dict]:
    """Today's published edition, if any."""
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return next((d for d in history if d.get("date") == date_str), None)

def send_notification(backend_url: str, token: str, entry: dict, poll_interval: Optional[float] = None, wake_timeout: Optional[float] = None) -> Tuple[bool, Optional[str]]:
    """Wakes the backend (Render cold start), then asks it to email subscribers.
    Only HTTP 200 counts as success. Never raises."""
    poll_interval = WAKE_POLL_SECONDS if poll_interval is None else poll_interval
    wake_timeout = WAKE_TIMEOUT_SECONDS if wake_timeout is None else wake_timeout

    deadline = time.monotonic() + wake_timeout
    last = "no response"
    while True:
        try:
            r = httpx.get(f"{backend_url}/api/status", timeout=15)
            if r.status_code == 200:
                break
            last = f"status check returned {r.status_code}"
        except Exception as e:
            last = f"status check failed: {e}"
        if time.monotonic() >= deadline:
            return False, f"Backend did not wake within {wake_timeout}s ({last})"
        time.sleep(poll_interval)

    payload = {"date": entry.get("date"), "published_at": entry.get("published_at"), "briefs": entry.get("briefs", [])}
    try:
        r = httpx.post(f"{backend_url}/api/notify-subscribers", json=payload, headers={"X-Auth-Token": token}, timeout=60)
    except Exception as e:
        return False, f"Notify request failed: {e}"
    if r.status_code == 200:
        return True, None
    return False, f"Notify returned {r.status_code}: {str(r.text)[:200]}"

def queue_email(run_state: dict, state_dir: Path, briefs: list):
    """Marks today's email pending (or skipped when there is no backend or nothing to send) and saves it,
    so a crash before sending still leaves the email for a later run."""
    run_state["email"]["status"] = "pending" if (os.getenv("BACKEND_API_URL") and briefs) else "skipped"
    save_state(state_dir, run_state)

def deliver_email(run_state: dict, state_dir: Path, entry: dict) -> bool:
    """Sends today's edition to subscribers and records the result. Returns False if the email is still pending."""
    email = run_state["email"]
    backend_url = os.getenv("BACKEND_API_URL")
    queue_email(run_state, state_dir, entry.get("briefs"))
    if email["status"] == "skipped":
        return True
    ok, err = send_notification(backend_url, os.getenv("NOTIFY_SECRET_TOKEN", ""), entry)
    if ok:
        email["status"] = "sent"
        email["last_error"] = None
        logger.info(f"Subscriber notification accepted for {entry.get('date')}.")
    else:
        email["attempts"] += 1
        email["last_error"] = err
        logger.error(f"Subscriber notification failed (attempt {email['attempts']}): {err}. A later run will retry.")
    save_state(state_dir, run_state)
    return ok

def main():
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    init_db()
    init_history_file()
    health.reset()

    runs_dir = DATA_DIR / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    state_dir = runs_dir / "state"
    min_briefs = int(os.getenv("MIN_BRIEFS", "3"))
    git_sha = get_git_sha()
    run_state = load_state(state_dir, date_str)

    # Already published today: only retry a pending email
    entry = todays_entry(HISTORY_FILE_PATH, date_str)
    if entry is not None:
        if run_state["email"]["status"] == "pending":
            logger.info(f"Edition for {date_str} already published; retrying the pending subscriber email.")
            if not deliver_email(run_state, state_dir, entry):
                sys.exit(1)
            return
        logger.info(f"Edition for {date_str} already published (email: {run_state['email']['status']}). Nothing to do.")
        return

    try:
        res = run_pipeline(run_state, state_dir, min_briefs, git_sha)
    except Exception as exc:
        # Stages finished before the crash stay saved; the next run resumes at the crashed stage
        logger.error(f"Graph execution failed: {exc}")
        health.mark_fallback("graph", str(exc))
        record_attempt(run_state, git_sha, first_unfinished_stage(run_state), f"Graph exception: {exc}")
        save_state(state_dir, run_state)
        with open(runs_dir / f"{date_str}.degraded.json", "w") as f:
            json.dump(build_run_snapshot(date_str, [], [f"Graph exception: {exc}"]), f, indent=2)
        sys.exit(1)

    if res is None:
        last = run_state["attempts"][-1]
        with open(runs_dir / f"{date_str}.degraded.json", "w") as f:
            json.dump(build_run_snapshot(date_str, [], [f"{last['failed_stage']}: {last['reason']}"]), f, indent=2)
        sys.exit(1)

    briefs = res.get("final_briefs", [])
    candidate_urls = {c.get("url") for c in res.get("researched_candidates", []) if c.get("url")}
    evidence_by_url = {c.get("url"): build_evidence(c, MAX_EVIDENCE_CHARS) for c in res.get("researched_candidates", []) if c.get("url")}

    published, reasons = publish_gate(briefs, candidate_urls, evidence_by_url, date_str, runs_dir, min_briefs, produced_count=len(briefs),
                                      on_approved=lambda approved: queue_email(run_state, state_dir, approved))
    if reasons:
        # Rerun only the editor next time, with the saved candidates
        mark_failed(run_state, "editor", "; ".join(reasons))
        record_attempt(run_state, git_sha, "editor", "; ".join(reasons))
        save_state(state_dir, run_state)
        sys.exit(1)

    entry = {"date": date_str, "published_at": datetime.now(timezone.utc).isoformat(), "briefs": published}
    if not deliver_email(run_state, state_dir, entry):
        sys.exit(1)

if __name__ == "__main__":
    main()
