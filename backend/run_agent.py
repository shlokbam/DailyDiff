"""
DailyDiff Pipeline Runner & Publish Gate.
Orchestrates graph execution, quality gate validation, snapshot creation, and publication.
"""

import os
import sys
import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import httpx

from app.config import DATA_DIR, ARCHIVE_DIR, HISTORY_FILE_PATH
from app.database import init_db, init_history_file, append_to_history
from app.run_health import health
from app.agents.graph import create_agent_graph
from app.agents.researcher import MAX_EVIDENCE_CHARS
from app.checks import validate_briefs, build_evidence

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("DailyDiff.runner")

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

def publish_gate(briefs: list, candidate_urls: set, evidence_by_url: dict, date_str: str, runs_dir: Path, min_briefs: int, produced_count: int):
    """Strict publish gate: drops invalid briefs, enforces categories, blocks on failure."""
    briefs, failure_reasons = check_briefs(briefs, produced_count, candidate_urls, evidence_by_url, min_briefs)

    if failure_reasons:
        logger.error(f"[GATE REJECTION] Degraded run for {date_str}: {failure_reasons}")
        degraded_path = runs_dir / f"{date_str}.degraded.json"
        with open(degraded_path, "w") as f:
            json.dump(build_run_snapshot(date_str, briefs, failure_reasons), f, indent=2)
        sys.exit(1)

    # 4. Gate passed: publish output
    logger.info(f"[GATE APPROVED] Publishing {len(briefs)} briefs for {date_str}...")
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

    # Notify subscribers if configured
    backend_url = os.getenv("BACKEND_API_URL")
    if backend_url and briefs:
        try:
            headers = {"X-Auth-Token": os.getenv("NOTIFY_SECRET_TOKEN", "")}
            payload = {"date": date_str, "published_at": datetime.now(timezone.utc).isoformat(), "briefs": briefs}
            httpx.post(f"{backend_url}/api/notify-subscribers", json=payload, headers=headers, timeout=60)
        except Exception as e:
            logger.error(f"Failed to dispatch subscriber notification: {e}")

def main():
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    init_db()
    init_history_file()
    health.reset()

    runs_dir = DATA_DIR / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    min_briefs = int(os.getenv("MIN_BRIEFS", "3"))

    logger.info("Executing DailyDiff graph workflow...")
    graph = create_agent_graph()
    try:
        res = graph.invoke({"raw_signals": [], "candidates": [], "researched_candidates": [], "vetted_candidates": [], "final_briefs": []})
    except Exception as exc:
        logger.error(f"Graph execution failed: {exc}")
        health.mark_fallback("graph", str(exc))
        with open(runs_dir / f"{date_str}.degraded.json", "w") as f:
            json.dump(build_run_snapshot(date_str, [], [f"Graph exception: {exc}"]), f, indent=2)
        sys.exit(1)

    briefs = res.get("final_briefs", [])
    candidate_urls = {c.get("url") for c in res.get("researched_candidates", []) if c.get("url")}
    evidence_by_url = {c.get("url"): build_evidence(c, MAX_EVIDENCE_CHARS) for c in res.get("researched_candidates", []) if c.get("url")}

    publish_gate(briefs, candidate_urls, evidence_by_url, date_str, runs_dir, min_briefs, produced_count=len(briefs))

if __name__ == "__main__":
    main()
