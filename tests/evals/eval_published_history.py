#!/usr/bin/env python3
"""
tests/evals/eval_published_history.py

Evaluates published history in data/history.json against production quality checks.
Python 3.12, offline.
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure repository root and backend are on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Suppress noisy warnings during batch verification
logging.getLogger("DailyDiff.checks").setLevel(logging.ERROR)

from app.checks import (
    count_at_most_5,
    categories_unique,
    required_fields_present,
    category_valid,
    has_bold_lead,
    no_tldr_label,
    verdict_valid,
    url_valid_https,
    is_generic_fallback_text,
    validate_briefs,
)
from tests.evals.metrics import fmt_rate

DEFAULT_HISTORY = BASE_DIR / "data" / "history.json"
DEFAULT_RUNS_DIR = BASE_DIR / "data" / "runs"
DEFAULT_OUT = BASE_DIR / "tests" / "evals" / "baselines" / "history_checks.json"


def evaluate_day(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a single history day's briefs against checks."""
    date_str = entry.get("date", "UNKNOWN")
    briefs = entry.get("briefs", [])

    check_results = {
        "count_at_most_5": count_at_most_5(briefs),
        "categories_unique": categories_unique(briefs),
        "required_fields_present": all(required_fields_present(b) for b in briefs) if briefs else False,
        "category_valid": all(category_valid(b) for b in briefs) if briefs else False,
        "has_bold_lead": all(has_bold_lead(b.get("description", "")) for b in briefs) if briefs else False,
        "no_tldr_label": all(no_tldr_label(b.get("description", "")) for b in briefs) if briefs else True,
        "verdict_valid": all(verdict_valid(b.get("verdict", "")) for b in briefs) if briefs else False,
        "url_valid_https": all(url_valid_https(b.get("source_url", "")) for b in briefs) if briefs else False,
        "no_generic_fallback": all(
            not is_generic_fallback_text(b.get("description", ""))
            and not is_generic_fallback_text(b.get("why_it_matters", ""))
            for b in briefs
        ) if briefs else True,
    }

    # Use validate_briefs without evidence_by_url or candidate_urls
    violations = validate_briefs(briefs)
    all_passed = len(violations) == 0 and all(check_results.values())

    return {
        "date": date_str,
        "number_of_briefs": len(briefs),
        "passed": all_passed,
        "checks": check_results,
        "violations": violations,
    }


def find_first_run_date(runs_dir: Path) -> Optional[str]:
    """Find the earliest run date in runs_dir (ignoring .degraded.json)."""
    if not runs_dir.exists():
        return None
    dates = []
    for p in runs_dir.glob("*.json"):
        if p.name.endswith(".degraded.json"):
            continue
        m = re.match(r"^(\d{4}-\d{2}-\d{2})\.json$", p.name)
        if m:
            dates.append(m.group(1))
    return min(dates) if dates else None


def partition_windows(
    per_date: List[Dict[str, Any]], first_run_date: Optional[str]
) -> List[Tuple[str, List[Dict[str, Any]]]]:
    """Partition dates into up to three windows."""
    w1_dates = [d for d in per_date if d["date"] < "2026-09-04"]
    windows: List[Tuple[str, List[Dict[str, Any]]]] = []

    if w1_dates:
        windows.append(("before 2026-09-04", w1_dates))

    if first_run_date:
        w2_dates = [d for d in per_date if "2026-09-04" <= d["date"] < first_run_date]
        w3_dates = [d for d in per_date if d["date"] >= first_run_date]
        if w2_dates:
            windows.append((f"from 2026-09-04 to {first_run_date} (pre-runs)", w2_dates))
        if w3_dates:
            windows.append((f"from {first_run_date} onward (snapshot runs)", w3_dates))
    else:
        w2_dates = [d for d in per_date if d["date"] >= "2026-09-04"]
        if w2_dates:
            windows.append(("from 2026-09-04 onward", w2_dates))

    return windows


def summarize_window(name: str, days: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(days)
    if n == 0:
        return {}
    k_passed = sum(1 for d in days if d["passed"])

    check_keys = [
        "count_at_most_5",
        "categories_unique",
        "required_fields_present",
        "category_valid",
        "has_bold_lead",
        "no_tldr_label",
        "verdict_valid",
        "url_valid_https",
        "no_generic_fallback",
    ]

    check_rates = {}
    for key in check_keys:
        k_check = sum(1 for d in days if d["checks"].get(key, False))
        check_rates[key] = {
            "passed": k_check,
            "total": n,
            "rate_fmt": fmt_rate(k_check, n),
        }

    return {
        "window": name,
        "days_count": n,
        "days_passed": k_passed,
        "pass_rate_fmt": fmt_rate(k_passed, n),
        "check_rates": check_rates,
    }


def run_history_evaluation(
    history_path: Path = DEFAULT_HISTORY,
    runs_dir: Path = DEFAULT_RUNS_DIR,
    out_path: Path = DEFAULT_OUT,
) -> Dict[str, Any]:
    """Run checks over history and output baseline file."""
    if not history_path.exists():
        raise FileNotFoundError(f"History file not found at {history_path}")

    with open(history_path, "r", encoding="utf-8") as f:
        history_data = json.load(f)

    # Sort history entries chronologically
    history_data = sorted(history_data, key=lambda x: x.get("date", ""))

    per_date_results = [evaluate_day(entry) for entry in history_data]
    first_run_date = find_first_run_date(runs_dir)

    windows = partition_windows(per_date_results, first_run_date)
    window_summaries = {}

    print("\n" + "=" * 70)
    print("DAILYDIFF PUBLISHED HISTORY CHECKS BASELINE")
    print("=" * 70)
    print("NOTE: History has no evidence text; skipped evidence-based numeric check.\n")

    for w_name, w_days in windows:
        summary = summarize_window(w_name, w_days)
        window_summaries[w_name] = summary
        print(f"--- Window: {w_name} ({len(w_days)} days) ---")
        print(f"  Overall Day Pass Rate: {summary['pass_rate_fmt']}")
        for chk, details in summary["check_rates"].items():
            print(f"    - {chk.ljust(25)}: {details['rate_fmt']}")
        print()

    out_obj = {
        "metadata": {
            "history_file": str(history_path),
            "total_days": len(per_date_results),
            "skipped_checks": ["evidence_based_numeric_tokens"],
            "note": "History has no evidence text; evidence-based numeric check skipped.",
        },
        "windows": window_summaries,
        "per_date": per_date_results,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_obj, f, indent=2)

    print(f"Baseline saved to {out_path}\n")
    return out_obj


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate published history against checks and write baseline."
    )
    parser.add_argument(
        "--history",
        type=Path,
        default=DEFAULT_HISTORY,
        help="Path to data/history.json",
    )
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=DEFAULT_RUNS_DIR,
        help="Path to data/runs directory",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Path to output baseline json",
    )
    args = parser.parse_args()

    run_history_evaluation(
        history_path=args.history,
        runs_dir=args.runs_dir,
        out_path=args.out,
    )


if __name__ == "__main__":
    main()
