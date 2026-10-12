import os
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.agents.verifier import verifier_node
from app.run_health import health

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DailyDiff.eval.verifier")

def run_verifier_eval(dataset_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Evaluates the Verifier node using real model calls.
    Never simulates or falls back to ground truth.
    On error or health fallback, affected cases are marked status='ERROR (fallback_used)' and excluded from scoring.
    """
    if dataset_path is None:
        dataset_path = str(BASE_DIR / "tests" / "evals" / "golden_dataset.json")

    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    test_cases = [item for item in dataset if item.get("ground_truth", {}).get("verifier")]
    n_total = len(test_cases)
    logger.info(f"Loaded {n_total} test cases for Verifier evaluation.")

    candidates = []
    for c in test_cases:
        candidates.append({
            "eval_id": c["id"],
            "title": c["input_signal"]["title"],
            "description": c["input_signal"].get("raw_description", ""),
            "detailed_content": c["input_signal"].get("scraped_docs", ""),
            "source": c["input_signal"].get("source", ""),
            "url": c["input_signal"].get("url", "")
        })

    vetted_ids = set()
    error_cases = {}
    chunk_size = 5

    for i in range(0, len(candidates), chunk_size):
        chunk = candidates[i:i + chunk_size]
        prev_fallbacks_len = len(health.fallbacks)
        try:
            state = {"researched_candidates": chunk}
            result = verifier_node(state)
            if len(health.fallbacks) > prev_fallbacks_len:
                recent = health.fallbacks[prev_fallbacks_len:]
                reason = recent[-1].get("reason", "Internal fallback used")
                logger.warning(f"Verifier chunk used internal fallback: {reason}")
                for c in chunk:
                    error_cases[c["eval_id"]] = "ERROR (fallback_used)"
                continue

            vetted_candidates = result.get("vetted_candidates", [])
            for v in vetted_candidates:
                eid = v.get("eval_id")
                if eid:
                    vetted_ids.add(eid)
                else:
                    for tc in test_cases:
                        if tc["input_signal"]["title"] == v.get("title"):
                            vetted_ids.add(tc["id"])
        except Exception as e:
            err_msg = str(e)
            logger.error(f"Verifier chunk execution error: {err_msg}")
            for c in chunk:
                error_cases[c["eval_id"]] = err_msg

    correct = 0
    adversarial_total = 0
    adversarial_caught = 0
    legit_total = 0
    legit_passed = 0
    case_results = []

    for c in test_cases:
        cid = c["id"]
        exp_status = c["ground_truth"]["verifier"]["expected_status"]

        if cid in error_cases:
            err_val = error_cases[cid]
            status_val = "ERROR (fallback_used)" if "fallback_used" in str(err_val) else "ERROR"
            case_results.append({
                "id": cid,
                "title": c["input_signal"]["title"],
                "archetype": c.get("archetype", ""),
                "expected_status": exp_status,
                "actual_status": status_val,
                "status": status_val,
                "passed": False,
                "error": err_val,
                "claim_summary": c["input_signal"].get("raw_description", c["input_signal"].get("description", "")),
                "documentation_snippet": c["input_signal"].get("scraped_docs", "")[:320],
                "flagged_contradiction": c["ground_truth"]["verifier"].get("flagged_contradiction"),
                "url": c["input_signal"].get("url", "")
            })
            continue

        act_status = "VALID" if cid in vetted_ids else "INVALID"
        passed = (act_status == exp_status)

        is_adversarial = (exp_status == "INVALID")
        if is_adversarial:
            adversarial_total += 1
            if act_status == "INVALID":
                adversarial_caught += 1
        else:
            legit_total += 1
            if act_status == "VALID":
                legit_passed += 1

        if passed:
            correct += 1

        case_results.append({
            "id": cid,
            "title": c["input_signal"]["title"],
            "archetype": c.get("archetype", ""),
            "expected_status": exp_status,
            "actual_status": act_status,
            "status": "EVALUATED",
            "passed": passed,
            "claim_summary": c["input_signal"].get("raw_description", c["input_signal"].get("description", "")),
            "documentation_snippet": c["input_signal"].get("scraped_docs", "")[:320],
            "flagged_contradiction": c["ground_truth"]["verifier"].get("flagged_contradiction"),
            "url": c["input_signal"].get("url", "")
        })

    n_error = len(error_cases)
    n_evaluated = n_total - n_error

    if n_evaluated > 0:
        accuracy = correct / n_evaluated
        adversarial_rate = adversarial_caught / adversarial_total if adversarial_total > 0 else 1.0
        false_rejection_rate = (legit_total - legit_passed) / legit_total if legit_total > 0 else 0.0
    else:
        accuracy, adversarial_rate, false_rejection_rate = 0.0, 0.0, 0.0

    eval_summary = {
        "node": "Verifier (Technical Fact-Checking & Anti-Hallucination)",
        "n_total": n_total,
        "n_evaluated": n_evaluated,
        "n_error": n_error,
        "accuracy": round(accuracy * 100, 1),
        "adversarial_catch_rate": round(adversarial_rate * 100, 1),
        "false_rejection_rate": round(false_rejection_rate * 100, 1),
        "adversarial_cases": adversarial_total,
        "adversarial_caught": adversarial_caught,
        "legit_cases": legit_total,
        "legit_passed": legit_passed,
        "details": case_results
    }

    return eval_summary

if __name__ == "__main__":
    report = run_verifier_eval()
    print("\n" + "=" * 55)
    print("VERIFIER EVALUATION REPORT:")
    print(f"Total Cases:             {report['n_total']}")
    print(f"Evaluated Cases:         {report['n_evaluated']}")
    print(f"Error Cases:             {report['n_error']}")
    print(f"Accuracy:                {report['accuracy']}%")
    print(f"Adversarial Catch Rate:  {report['adversarial_catch_rate']}%")
    print(f"False Rejection Rate:    {report['false_rejection_rate']}%")
    print("=" * 55)
    for c in report["details"]:
        status = c["status"]
        pass_label = "PASS" if c["passed"] else ("ERROR" if status == "ERROR" else "FAIL")
        print(f"[{pass_label}] {c['id']}: {c['title'][:36]:<36} | Exp: {c['expected_status']} | Act: {c['actual_status']}")
