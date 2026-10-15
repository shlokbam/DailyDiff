"""
Skeptic evaluation on 25 golden signals.
Reference-based: reports confusion counts (TP, FP, TN, FN), precision, recall, accuracy,
and scope drift (correct rejection of enterprise, math, finance, and duplicate releases).
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.agents.skeptic import deduplicate_and_filter_node
from app.run_health import health
from tests.evals.common import load_dataset, rate

logger = logging.getLogger("DailyDiff.eval.skeptic")

def run_skeptic_eval(chunk_size: int = 5) -> Dict[str, Any]:
    cases = load_dataset()
    tp, fp, tn, fn = 0, 0, 0, 0
    errors = 0
    scope_drift_total = 0
    scope_drift_rejected = 0
    results_by_case = {}

    with patch("app.agents.skeptic.get_published_urls", return_value=set()), patch("app.agents.skeptic.extract_history_summary", return_value="No past briefs have been published yet."):
        for i in range(0, len(cases), chunk_size):
            chunk = cases[i:i + chunk_size]
            signals = [c["input_signal"] for c in chunk]
            health.reset()

            try:
                out = deduplicate_and_filter_node({"raw_signals": signals})
                if health.has_fallbacks or health.llm_errors_count > 0:
                    for c in chunk:
                        errors += 1
                        results_by_case[c["id"]] = {"passed": False, "status": "ERROR", "reason": "LLM fallback/error"}
                    continue

                kept_urls = {c["url"].strip().rstrip("/").lower() for c in out.get("candidates", []) if c.get("url")}
                for c in chunk:
                    cid = c["id"]
                    exp = c["ground_truth"]["skeptic"]["expected_decision"]
                    url = c["input_signal"].get("url", "").strip().rstrip("/").lower()
                    act = "KEEP" if url in kept_urls else "REJECT"
                    passed = (exp == act)

                    if exp == "REJECT":
                        scope_drift_total += 1
                        if act == "REJECT":
                            scope_drift_rejected += 1

                    if exp == "KEEP" and act == "KEEP":
                        tp += 1
                    elif exp == "REJECT" and act == "KEEP":
                        fp += 1
                    elif exp == "REJECT" and act == "REJECT":
                        tn += 1
                    elif exp == "KEEP" and act == "REJECT":
                        fn += 1

                    results_by_case[cid] = {
                        "passed": passed,
                        "status": "PASS" if passed else "FAIL",
                        "expected": exp,
                        "actual": act,
                        "archetype": c.get("archetype", ""),
                    }

            except Exception as e:
                logger.error(f"Skeptic eval exception on chunk {i}: {e}")
                for c in chunk:
                    errors += 1
                    results_by_case[c["id"]] = {"passed": False, "status": "ERROR", "reason": str(e)}

    evaluated = tp + fp + tn + fn
    acc_str = rate(tp + tn, evaluated) if evaluated > 0 else "0/0 = 0%"
    prec_str = rate(tp, tp + fp) if (tp + fp) > 0 else "0/0 = 0%"
    rec_str = rate(tp, tp + fn) if (tp + fn) > 0 else "0/0 = 0%"
    drift_str = rate(scope_drift_rejected, scope_drift_total) if scope_drift_total > 0 else "0/0 = 0%"

    print("\n--- SKEPTIC EVALUATION (25 Golden Signals) ---")
    print(f"Confusion Matrix: TP={tp}, FP={fp}, TN={tn}, FN={fn} | Errors={errors}")
    print(f"Accuracy:    {acc_str}")
    print(f"Precision:   {prec_str}")
    print(f"Recall:      {rec_str}")
    print(f"Scope Drift: Correctly rejected should-reject: {drift_str}")

    return {
        "node": "skeptic",
        "total_cases": len(cases),
        "evaluated": evaluated,
        "errors": errors,
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "accuracy": acc_str,
        "precision": prec_str,
        "recall": rec_str,
        "scope_drift_rejected": drift_str,
        "cases": results_by_case,
    }

if __name__ == "__main__":
    run_skeptic_eval()
