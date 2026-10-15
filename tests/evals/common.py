"""
Common evaluation utilities for DailyDiff.
Provides dataset loaders, safe node execution, Wilson confidence interval helper,
and results comparison functions.
"""

import os
import sys
import json
import math
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.run_health import health

EVALS_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EVALS_DIR / "results"

def load_dataset(filename: str = "golden_dataset.json") -> List[Dict[str, Any]]:
    path = EVALS_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_planted_errors() -> List[Dict[str, Any]]:
    return load_dataset("planted_errors.json")

def wilson_interval(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score confidence interval for a binomial proportion."""
    if n <= 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + (z ** 2) / n
    center = (p + (z ** 2) / (2 * n)) / denom
    spread = (z * math.sqrt((p * (1 - p) + (z ** 2) / (4 * n)) / n)) / denom
    return (max(0.0, center - spread), min(1.0, center + spread))

def rate(k: int, n: int) -> str:
    """Formats count k out of n as a percentage with Wilson confidence interval."""
    if n <= 0:
        return "n/a (no cases)"
    pct = round(100.0 * k / n)
    low, high = wilson_interval(k, n)
    return f"{k}/{n} = {pct}% (with this few cases, roughly {round(low * 100)}-{round(high * 100)}%)"

def run_node_safely(node_fn: Callable, state: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Executes an agent node safely. Detects whether it used a hard fallback or encountered an LLM error.
    Returns (result, None) on clean execution, or (None, error_reason) on failure.
    """
    health.reset()
    try:
        res = node_fn(state)
        if health.has_fallbacks:
            err = health.fallbacks[0].get("reason", "Node triggered fallback")
            return None, f"Fallback: {err}"
        if health.llm_errors_count > 0:
            return None, "LLM API error occurred during invocation"
        return res, None
    except Exception as e:
        return None, f"Exception: {str(e)}"

def save_results(data: Dict[str, Any], timestamp: Optional[str] = None) -> Tuple[Path, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = timestamp or time.strftime("%Y%m%d_%H%M%S")
    run_file = RESULTS_DIR / f"run_{ts}.json"
    latest_file = RESULTS_DIR / "latest.json"

    with open(run_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return run_file, latest_file

def compare_results(current: Dict[str, Any], previous: Optional[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Compares current eval results with a previous run, reporting regressions and fixes."""
    diff = {"regressions": [], "fixes": []}
    if not previous:
        return diff

    curr_cases = current.get("cases", {})
    prev_cases = previous.get("cases", {})

    for case_id, curr_res in curr_cases.items():
        if case_id in prev_cases:
            c_pass = curr_res.get("passed", False)
            p_pass = prev_cases[case_id].get("passed", False)
            if not c_pass and p_pass:
                diff["regressions"].append(f"Case '{case_id}' regressed from PASS to FAIL/ERROR")
            elif c_pass and not p_pass:
                diff["fixes"].append(f"Case '{case_id}' fixed from FAIL to PASS")

    return diff
