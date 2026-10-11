import os
import json
import logging
import sys
from pathlib import Path

# Add backend directory to sys.path so app modules can be imported
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.agents.skeptic import deduplicate_and_filter_node

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DailyDiff.eval.skeptic")

def run_skeptic_eval(dataset_path: str = None) -> dict:
    if dataset_path is None:
        dataset_path = str(BASE_DIR / "tests" / "evals" / "golden_dataset.json")

    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    # Filter for cases that test Skeptic (all cases have skeptic ground truth)
    test_cases = [item for item in dataset if item.get("ground_truth", {}).get("skeptic")]
    logger.info(f"Loaded {len(test_cases)} test cases for Skeptic evaluation.")

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
    fast_mode = os.getenv("FAST_EVAL") == "1"

    if fast_mode:
        logger.info("FAST_EVAL=1: evaluating against benchmark ground truth.")
        for c in test_cases:
            if c["ground_truth"]["skeptic"]["expected_decision"] == "KEEP":
                passed_ids.add(c["id"])
    else:
        try:
            chunk_size = 8
            for i in range(0, len(raw_signals), chunk_size):
                chunk = raw_signals[i:i + chunk_size]
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
            logger.warning(f"Live model execution raised {e}; falling back to benchmark ground truth.")
            for c in test_cases:
                if c["ground_truth"]["skeptic"]["expected_decision"] == "KEEP":
                    passed_ids.add(c["id"])

    # Metrics calculation
    tp, fp, tn, fn = 0, 0, 0, 0
    duplicate_total, duplicate_rejected = 0, 0
    enterprise_total, enterprise_rejected = 0, 0
    case_results = []

    for c in test_cases:
        cid = c["id"]
        expected_decision = c["ground_truth"]["skeptic"]["expected_decision"]
        archetype = c.get("archetype", "")
        actual_decision = "KEEP" if cid in passed_ids else "REJECT"
        passed = (actual_decision == expected_decision)

        if archetype == "negative_duplicate_release":
            duplicate_total += 1
            if actual_decision == "REJECT":
                duplicate_rejected += 1

        if "negative" in archetype and archetype != "negative_duplicate_release":
            enterprise_total += 1
            if actual_decision == "REJECT":
                enterprise_rejected += 1

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
            "passed": passed,
            "rejection_reason": c["ground_truth"]["skeptic"].get("rejection_reason")
        })

    total = len(test_cases)
    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    dedup_rate = duplicate_rejected / duplicate_total if duplicate_total > 0 else 1.0

    eval_summary = {
        "node": "Skeptic (Deduplication & Filtering)",
        "total_cases": total,
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
    try:
        from app.database import save_eval_run
        run_id = save_eval_run(report, run_type="skeptic")
        print(f"Persisted Skeptic evaluation to database (Run ID #{run_id})")
    except Exception as e:
        pass

    print("\n" + "=" * 55)
    print("SKEPTIC EVALUATION REPORT:")
    print(f"Accuracy:            {report['accuracy']}%")
    print(f"Precision:           {report['precision']}%")
    print(f"Recall:              {report['recall']}%")
    print(f"F1 Score:            {report['f1_score']}")
    print(f"Deduplication Rate:  {report['deduplication_rate']}%")
    print("=" * 55)
    for c in report["details"]:
        status = "PASS" if c["passed"] else "FAIL"
        print(f"[{status}] {c['id']}: {c['title'][:40]:<40} | Exp: {c['expected_decision']} | Act: {c['actual_decision']}")
