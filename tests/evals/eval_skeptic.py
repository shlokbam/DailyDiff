import os
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.agents.skeptic import deduplicate_and_filter_node

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DailyDiff.eval.skeptic")

def run_skeptic_eval(dataset_path: Optional[str] = None, one_call: bool = False) -> Dict[str, Any]:
    """
    Evaluates the Skeptic node using real model calls.
    Never simulates or falls back to ground truth.
    On error, affected cases are marked status='ERROR' and metrics are computed only over evaluated cases.
    """
    if dataset_path is None:
        dataset_path = str(BASE_DIR / "tests" / "evals" / "golden_dataset.json")

    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    test_cases = [item for item in dataset if item.get("ground_truth", {}).get("skeptic")]
    n_total = len(test_cases)
    logger.info(f"Loaded {n_total} test cases for Skeptic evaluation.")

    # Convert dataset input signals into format expected by skeptic node
    raw_signals = []
    for c in test_cases:
        sig = c["input_signal"].copy()
        sig["description"] = sig.get("raw_description", sig.get("description", ""))
        sig["eval_id"] = c["id"]
        if c.get("archetype") != "negative_duplicate_release":
            orig_url = sig.get("url", "")
            sig["url"] = f"{orig_url}?eval_bench=1" if orig_url else ""
        raw_signals.append(sig)

    passed_ids = set()
    error_cases = {}

    is_one_call = one_call or ("--one-call" in sys.argv)
    chunk_size = len(raw_signals) if is_one_call else 8

    for i in range(0, len(raw_signals), chunk_size):
        chunk = raw_signals[i:i + chunk_size]
        try:
            state = {"raw_signals": chunk}
            result = deduplicate_and_filter_node(state)
            passed_candidates = result.get("candidates", [])
            for cand in passed_candidates:
                eid = cand.get("eval_id")
                if eid:
                    passed_ids.add(eid)
                else:
                    for tc in test_cases:
                        if tc["input_signal"]["title"] == cand.get("title"):
                            passed_ids.add(tc["id"])
        except Exception as e:
            err_msg = str(e)
            logger.error(f"Skeptic chunk execution error: {err_msg}")
            for c in chunk:
                error_cases[c["eval_id"]] = err_msg

    case_results = []
    tp, fp, tn, fn = 0, 0, 0, 0
    duplicate_total, duplicate_rejected = 0, 0

    for c in test_cases:
        cid = c["id"]
        expected_decision = c["ground_truth"]["skeptic"]["expected_decision"]
        archetype = c.get("archetype", "")

        if cid in error_cases:
            case_results.append({
                "id": cid,
                "title": c["input_signal"]["title"],
                "archetype": archetype,
                "expected_decision": expected_decision,
                "actual_decision": "ERROR",
                "status": "ERROR",
                "passed": False,
                "error": error_cases[cid],
                "rejection_reason": c["ground_truth"]["skeptic"].get("rejection_reason")
            })
            continue

        actual_decision = "KEEP" if cid in passed_ids else "REJECT"
        passed = (actual_decision == expected_decision)

        if archetype == "negative_duplicate_release":
            duplicate_total += 1
            if actual_decision == "REJECT":
                duplicate_rejected += 1

        if expected_decision == "KEEP":
            if actual_decision == "KEEP":
                tp += 1
            else:
                fn += 1
        else:
            if actual_decision == "REJECT":
                tn += 1
            else:
                fp += 1

        case_results.append({
            "id": cid,
            "title": c["input_signal"]["title"],
            "archetype": archetype,
            "expected_decision": expected_decision,
            "actual_decision": actual_decision,
            "status": "EVALUATED",
            "passed": passed,
            "rejection_reason": c["ground_truth"]["skeptic"].get("rejection_reason")
        })

    n_error = len(error_cases)
    n_evaluated = n_total - n_error

    if n_evaluated > 0:
        accuracy = (tp + tn) / n_evaluated
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        dedup_rate = duplicate_rejected / duplicate_total if duplicate_total > 0 else 1.0
    else:
        accuracy, precision, recall, f1, dedup_rate = 0.0, 0.0, 0.0, 0.0, 0.0

    eval_summary = {
        "node": "Skeptic (Deduplication & Filtering)",
        "n_total": n_total,
        "n_evaluated": n_evaluated,
        "n_error": n_error,
        "accuracy": round(accuracy * 100, 1),
        "precision": round(precision * 100, 1),
        "recall": round(recall * 100, 1),
        "f1_score": round(f1, 3),
        "deduplication_rate": round(dedup_rate * 100, 1),
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "details": case_results
    }

    return eval_summary

if __name__ == "__main__":
    report = run_skeptic_eval()
    print("\n" + "=" * 55)
    print("SKEPTIC EVALUATION REPORT:")
    print(f"Total Cases:         {report['n_total']}")
    print(f"Evaluated Cases:     {report['n_evaluated']}")
    print(f"Error Cases:         {report['n_error']}")
    print(f"Accuracy:            {report['accuracy']}%")
    print(f"Precision:           {report['precision']}%")
    print(f"Recall:              {report['recall']}%")
    print(f"F1 Score:            {report['f1_score']}")
    print(f"Deduplication Rate:  {report['deduplication_rate']}%")
    print("=" * 55)
    for c in report["details"]:
        status = c["status"]
        pass_label = "PASS" if c["passed"] else ("ERROR" if status == "ERROR" else "FAIL")
        print(f"[{pass_label}] {c['id']}: {c['title'][:36]:<36} | Exp: {c['expected_decision']} | Act: {c['actual_decision']}")
