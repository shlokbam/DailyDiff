import os
import sys
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "backend"))

from tests.evals.run_meta import (
    ensure_api_keys,
    enable_model_tracking,
    build_run_meta,
    verify_live_guards,
    TRACKER
)
from tests.evals.eval_skeptic import run_skeptic_eval
from tests.evals.eval_verifier import run_verifier_eval
from tests.evals.eval_analyst import run_analyst_eval
from tests.evals.eval_editor import run_editor_eval

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DailyDiff.eval.runner")

def run_all_evaluations(smoke: bool = False, allow_errors: bool = False) -> dict:
    mode = "smoke" if smoke or ("--smoke" in sys.argv) else "live"

    if mode == "smoke":
        print("\n" + "=" * 60)
        print("SMOKE RUN - NOT A MODEL MEASUREMENT")
        print("=" * 60 + "\n")
    else:
        # Strict guard: Fail immediately if live mode has no valid LLM keys
        ensure_api_keys(mode="live")

    enable_model_tracking(mode)

    started_at = datetime.now(timezone.utc).isoformat()
    start_time = time.time()

    # 1. Skeptic Node Eval
    logger.info("Executing 1/4: Skeptic Evaluation...")
    skeptic_report = run_skeptic_eval()

    # 2. Verifier Node Eval
    logger.info("Executing 2/4: Verifier Evaluation...")
    verifier_report = run_verifier_eval()

    # 3. Analyst Node Eval
    logger.info("Executing 3/4: Analyst Evaluation...")
    analyst_report = run_analyst_eval()

    # 4. Editor Node Eval
    logger.info("Executing 4/4: Editor Evaluation...")
    editor_report = run_editor_eval()

    elapsed = time.time() - start_time
    finished_at = datetime.now(timezone.utc).isoformat()

    meta = build_run_meta(
        mode=mode,
        started_at=started_at,
        finished_at=finished_at,
        wall_seconds=elapsed
    )

    if mode == "live":
        verify_live_guards(meta)

    overall_report = {
        "meta": meta,
        "summary": {
            "skeptic_accuracy": skeptic_report["accuracy"],
            "skeptic_f1": skeptic_report["f1_score"],
            "skeptic_deduplication_rate": skeptic_report["deduplication_rate"],
            "skeptic_evaluated": skeptic_report["n_evaluated"],
            "skeptic_total": skeptic_report["n_total"],
            "skeptic_errors": skeptic_report["n_error"],

            "verifier_accuracy": verifier_report["accuracy"],
            "verifier_adversarial_catch_rate": verifier_report["adversarial_catch_rate"],
            "verifier_false_rejection_rate": verifier_report["false_rejection_rate"],
            "verifier_evaluated": verifier_report["n_evaluated"],
            "verifier_total": verifier_report["n_total"],
            "verifier_errors": verifier_report["n_error"],

            "analyst_verdict_accuracy": analyst_report["verdict_accuracy"],
            "analyst_audience_specificity": analyst_report["audience_specificity_rate"],
            "analyst_practicality_score": analyst_report["average_practicality_score"],
            "analyst_evaluated": analyst_report["n_evaluated"],
            "analyst_total": analyst_report["n_total"],
            "analyst_errors": analyst_report["n_error"],

            "editor_format_compliance": editor_report["format_compliance_rate"],
            "editor_category_uniqueness": editor_report["category_uniqueness_rate"],
            "editor_readability_score": editor_report["average_readability_score"],
            "editor_evaluated": editor_report["n_evaluated"],
            "editor_total": editor_report["n_total"],
            "editor_errors": editor_report["n_error"]
        },
        "nodes": {
            "skeptic": skeptic_report,
            "verifier": verifier_report,
            "analyst": analyst_report,
            "editor": editor_report
        }
    }

    total_errors = (
        skeptic_report["n_error"]
        + verifier_report["n_error"]
        + analyst_report["n_error"]
        + editor_report["n_error"]
    )
    has_node_error = total_errors > 0

    if has_node_error:
        if allow_errors or ("--allow-errors" in sys.argv):
            meta["incomplete"] = True
            overall_report["meta"]["incomplete"] = True
        else:
            print("\n" + "=" * 60)
            print("[FAILURE] Evaluation run encountered node errors:")
            print(f"  Skeptic errors:  {skeptic_report['n_error']}")
            print(f"  Verifier errors: {verifier_report['n_error']}")
            print(f"  Analyst errors:  {analyst_report['n_error']}")
            print(f"  Editor errors:   {editor_report['n_error']}")
            print("Run not persisted because --allow-errors was not set. Exiting 1.")
            print("=" * 60 + "\n")
            sys.exit(1)

    # Handling persistence & output files based on mode
    if mode == "smoke":
        smoke_results_path = BASE_DIR / "tests" / "evals" / "smoke_results.json"
        with open(smoke_results_path, "w") as f:
            json.dump(overall_report, f, indent=2)
        logger.info(f"Saved smoke results to {smoke_results_path}")
    else:
        # LIVE RUN: Save to database and public result files
        try:
            from app.database import save_eval_run
            run_id = save_eval_run(overall_report, run_type="full_suite")
            overall_report["db_run_id"] = run_id
            logger.info(f"Persisted live evaluation run #{run_id} to database.")
        except Exception as db_err:
            logger.warning(f"Database save error: {db_err}")

        results_path = BASE_DIR / "tests" / "evals" / "eval_results.json"
        with open(results_path, "w") as f:
            json.dump(overall_report, f, indent=2)

        frontend_public_dir = BASE_DIR / "frontend" / "public"
        frontend_public_dir.mkdir(parents=True, exist_ok=True)
        frontend_results_path = frontend_public_dir / "eval_results.json"
        with open(frontend_results_path, "w") as f:
            json.dump(overall_report, f, indent=2)
        logger.info(f"Saved live results to {results_path} and {frontend_results_path}")

    return overall_report

if __name__ == "__main__":
    is_smoke = "--smoke" in sys.argv
    has_allow_errors = "--allow-errors" in sys.argv

    try:
        report = run_all_evaluations(smoke=is_smoke, allow_errors=has_allow_errors)
    except Exception as e:
        print(f"\n[FATAL] Evaluation failed: {e}")
        sys.exit(1)

    s = report["summary"]
    m = report["meta"]

    print("\n" + "=" * 60)
    print(f"DAILYDIFF EVALUATION REPORT [{m['mode'].upper()}]")
    print(f"Mode:               {m['mode']}")
    print(f"Total Runtime:      {m['wall_seconds']}s")
    print(f"LLM Calls Made:     {m['n_llm_calls']} (Errors: {m['n_llm_errors']})")
    print(f"Models Used:        {m['models_used']}")
    print("-" * 60)
    print(f"1. Skeptic:  Evaluated {s['skeptic_evaluated']}/{s['skeptic_total']} | Errors: {s['skeptic_errors']} | Acc: {s['skeptic_accuracy']}%")
    print(f"2. Verifier: Evaluated {s['verifier_evaluated']}/{s['verifier_total']} | Errors: {s['verifier_errors']} | Anti-Hype: {s['verifier_adversarial_catch_rate']}%")
    print(f"3. Analyst:  Evaluated {s['analyst_evaluated']}/{s['analyst_total']} | Errors: {s['analyst_errors']} | Specificity: {s['analyst_audience_specificity']}%")
    print(f"4. Editor:   Evaluated {s['editor_evaluated']}/{s['editor_total']} | Errors: {s['editor_errors']} | Compliance: {s['editor_format_compliance']}%")
    print("=" * 60)

    total_errors = s['skeptic_errors'] + s['verifier_errors'] + s['analyst_errors'] + s['editor_errors']
    if total_errors > 0 and not has_allow_errors:
        print(f"\n[FAILURE] Run ended with {total_errors} node errors. Exiting code 1.")
        sys.exit(1)
