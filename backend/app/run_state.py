"""
Per-day pipeline progress file (data/runs/state/YYYY-MM-DD.json).
Lets a later run resume from the failed stage and retry a pending email.
"""

import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Iterable, Optional

logger = logging.getLogger("DailyDiff.run_state")

# Graph node names, in execution order
STAGES = ["scout", "skeptic", "research", "verify", "analyze", "editor"]


def new_state(date_str: str) -> Dict[str, Any]:
    return {
        "date": date_str,
        "stages": {},
        "rejected_urls": [],
        "restarted": False,
        "email": {"status": "not_started", "attempts": 0, "last_error": None},
        "attempts": [],
    }


def load_state(state_dir: Path, date_str: str) -> Dict[str, Any]:
    """Today's state, or a fresh one if the file is missing or unreadable."""
    path = Path(state_dir) / f"{date_str}.json"
    if not path.exists():
        return new_state(date_str)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Unreadable run state {path} ({e}). Starting fresh.")
        return new_state(date_str)


def save_state(state_dir: Path, state: Dict[str, Any]):
    """Atomic write: a crash mid-save never leaves a half-written file."""
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / f"{state['date']}.json"
    tmp = state_dir / f"{state['date']}.json.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, path)


def mark_done(state: Dict[str, Any], stage: str, output: Dict[str, Any]):
    state["stages"][stage] = {"status": "done", "output": output}


def mark_failed(state: Dict[str, Any], stage: str, reason: str):
    state["stages"][stage] = {"status": "failed", "reason": str(reason)}


def first_unfinished_stage(state: Dict[str, Any]) -> Optional[str]:
    for stage in STAGES:
        if state["stages"].get(stage, {}).get("status") != "done":
            return stage
    return None


def merged_outputs(state: Dict[str, Any]) -> Dict[str, Any]:
    """Outputs of finished stages combined in order; later stages overwrite earlier keys."""
    merged: Dict[str, Any] = {}
    for stage in STAGES:
        info = state["stages"].get(stage, {})
        if info.get("status") == "done":
            merged.update(info.get("output") or {})
    return merged


def reset_stages(state: Dict[str, Any]):
    """Forget all stage results (restart from Scout). Keeps rejected URLs, the restart flag, email and attempts."""
    state["stages"] = {}


def add_rejected_urls(state: Dict[str, Any], urls: Iterable[str]):
    for url in urls:
        if url and url not in state["rejected_urls"]:
            state["rejected_urls"].append(url)


def record_attempt(state: Dict[str, Any], git_sha: str, failed_stage: Optional[str], reason: Optional[str]):
    state["attempts"].append({
        "started_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha,
        "failed_stage": failed_stage,
        "reason": reason,
    })
