"""
Master evaluation runner for DailyDiff.
Runs all component evals and the end-to-end pipeline eval.
Prints a single plain summary table (counts first, then percentages),
saves results to JSON, compares against previous runs for regressions/fixes,
and exits with code 1 if any case encountered an ERROR.
"""

import sys
import os
import json
import time
from pathlib import Path

# Add repo root and backend directory to path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BASE_DIR / "backend") not in sys.path:
    sys.path.insert(0, str(BASE_DIR / "backend"))

from tests.evals.eval_skeptic import run_skeptic_eval
from tests.evals.eval_verifier import run_verifier_eval
from tests.evals.eval_analyst import run_analyst_eval
from tests.evals.eval_editor import run_editor_eval
from tests.evals.eval_pipeline import run_pipeline_eval
from tests.evals.eval_history import run_history_eval
from tests.evals.common import save_results, compare_results, RESULTS_DIR

def run_all():
    print("=" * 70)
    print("DAILYDIFF COMPREHENSIVE EVALUATION SUITE")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print("=" * 70)

    # Load previous latest run for regression analysis
    prev_run = None
    latest_file = RESULTS_DIR / "latest.json"
    if latest_file.exists():
        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                prev_run = json.load(f)
        except Exception:
            pass

    # Run evaluations
    skeptic_res = run_skeptic_eval()
    verifier_res = run_verifier_eval()
    analyst_res = run_analyst_eval()
    editor_res = run_editor_eval()
    pipeline_res = run_pipeline_eval()
    history_res = run_history_eval()

    # Aggregate cases
    all_cases = {}
    for res in [skeptic_res, verifier_res, analyst_res]:
        for cid, info in res.get("cases", {}).items():
            all_cases[f"{res['node']}_{cid}"] = info

    total_errors = (
        skeptic_res.get("errors", 0)
        + verifier_res.get("errors", 0)
        + analyst_res.get("errors", 0)
        + (1 if editor_res.get("status") == "ERROR" else 0)
    )

    # Build master summary
    summary_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_errors": total_errors,
        "skeptic": skeptic_res,
        "verifier": verifier_res,
        "analyst": analyst_res,
        "editor": editor_res,
        "pipeline": pipeline_res,
        "history": history_res,
        "cases": all_cases,
    }

    # Save to evals results and frontend public
    run_file, latest_file = save_results(summary_data)
    frontend_public = BASE_DIR / "frontend" / "public" / "eval_results.json"
    frontend_public.parent.mkdir(parents=True, exist_ok=True)
    with open(frontend_public, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    # Sync benchmark datasets to frontend/public
    for ds_name in ["golden_dataset.json", "planted_errors.json"]:
        src = BASE_DIR / "tests" / "evals" / ds_name
        dst = BASE_DIR / "frontend" / "public" / ds_name
        if src.exists():
            with open(src, "r", encoding="utf-8") as sf, open(dst, "w", encoding="utf-8") as df:
                df.write(sf.read())


    # Check for regressions
    comparison = compare_results(summary_data, prev_run)

    # Print clean table
    print("\n" + "=" * 80)
    print(f"{'Node':12} | {'Metric':30} | {'Count & Rate':32}")
    print("-" * 80)
    print(f"{'Skeptic':12} | {'Accuracy':30} | {skeptic_res.get('accuracy', 'N/A')}")
    print(f"{'Skeptic':12} | {'Precision':30} | {skeptic_res.get('precision', 'N/A')}")
    print(f"{'Skeptic':12} | {'Recall':30} | {skeptic_res.get('recall', 'N/A')}")
    print(f"{'Skeptic':12} | {'Scope Drift Filtered':30} | {skeptic_res.get('scope_drift_rejected', 'N/A')}")
    print(f"{'Verifier':12} | {'Bad Items Caught':30} | {verifier_res.get('bad_caught', 'N/A')}")
    print(f"{'Verifier':12} | {'Good Items Wrongly Rejected':30} | {verifier_res.get('good_wrongly_rejected', 'N/A')}")
    print(f"{'Verifier':12} | {'Prompt Injections Succeeded':30} | {verifier_res.get('injections_succeeded', 'N/A')}")
    print(f"{'Analyst':12} | {'Verdict Match (Ref-based)':30} | {analyst_res.get('verdict_match_rate', 'N/A')}")
    print(f"{'Analyst':12} | {'G-Eval Usefulness Avg':30} | {analyst_res.get('usefulness_avg', 0.0):.2f} (>=0.7: {analyst_res.get('usefulness_gte_70', 'N/A')})")
    print(f"{'Editor':12} | {'Rule Checks Passed':30} | {editor_res.get('rule_checks', {}).get('required_fields', 'N/A')}")
    print(f"{'Editor':12} | {'G-Eval Faithfulness Avg':30} | {editor_res.get('faithfulness_avg', 0.0):.2f}")
    print(f"{'Pipeline':12} | {'Bad Items Leaked':30} | {pipeline_res.get('bad_items_leaked', 0)}/6 (Expected: 0/6)")
    print(f"{'Pipeline':12} | {'Gate Decision':30} | {pipeline_res.get('gate_decision', 'N/A')}")
    print(f"{'Pipeline':12} | {'Total Duration':30} | {pipeline_res.get('operational', {}).get('total_time', 0.0)}s")
    print("=" * 80)

    if comparison.get("regressions"):
        print("\nREGRESSIONS DETECTED:")
        for reg in comparison["regressions"]:
            print(f"  [!] {reg}")
    if comparison.get("fixes"):
        print("\nFIXES DETECTED:")
        for fix in comparison["fixes"]:
            print(f"  [*] {fix}")

    print(f"\nResults written to:\n  - {run_file}\n  - {latest_file}\n  - {frontend_public}")

    if total_errors > 0:
        print(f"\nFAILED: {total_errors} cases produced ERRORS during evaluation.")
        sys.exit(1)
    else:
        print("\nAll evaluation cases executed cleanly without errors.")
        sys.exit(0)

if __name__ == "__main__":
    run_all()
