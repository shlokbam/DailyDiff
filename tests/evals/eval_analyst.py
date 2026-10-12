import os
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.agents.analyst import analyst_node
from app.run_health import health

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DailyDiff.eval.analyst")

def score_practicality(text: str) -> float:
    """Heuristic rubric score for practical engineering takeaway (1 to 5 scale)."""
    if not text or len(text) < 20:
        return 1.0

    score = 2.0
    action_words = ["build", "learn", "deploy", "save", "debug", "prevent", "eliminate", "automate", "test", "run", "monitor", "optimize"]
    found_actions = sum(1 for w in action_words if re.search(r"\b" + w, text.lower()))
    if found_actions >= 1:
        score += 1.0
    if found_actions >= 2:
        score += 1.0

    if "good tool" in text.lower() or "notable development" in text.lower():
        score -= 1.0

    if len(text) > 80:
        score += 1.0

    return min(5.0, max(1.0, score))

def run_analyst_eval(dataset_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Evaluates the Analyst node using real model calls.
    Never simulates or falls back to ground truth.
    On error or health fallback, affected cases are marked status='ERROR (fallback_used)' and excluded from scoring.
    """
    if dataset_path is None:
        dataset_path = str(BASE_DIR / "tests" / "evals" / "golden_dataset.json")

    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    test_cases = [item for item in dataset if item.get("ground_truth", {}).get("analyst")]
    n_total = len(test_cases)
    logger.info(f"Loaded {n_total} test cases for Analyst evaluation.")

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

    analyzed_candidates = []
    error_cases = {}
    chunk_size = 6

    for i in range(0, len(candidates), chunk_size):
        chunk = candidates[i:i + chunk_size]
        prev_fallbacks_len = len(health.fallbacks)
        try:
            state = {"vetted_candidates": chunk}
            result = analyst_node(state)
            if len(health.fallbacks) > prev_fallbacks_len:
                recent = health.fallbacks[prev_fallbacks_len:]
                reason = recent[-1].get("reason", "Internal fallback used")
                logger.warning(f"Analyst chunk used internal fallback: {reason}")
                for c in chunk:
                    error_cases[c["eval_id"]] = "ERROR (fallback_used)"
                continue

            analyzed_candidates.extend(result.get("vetted_candidates", []))
        except Exception as e:
            err_msg = str(e)
            logger.error(f"Analyst chunk execution error: {err_msg}")
            for c in chunk:
                error_cases[c["eval_id"]] = err_msg

    analyzed_map = {}
    for a in analyzed_candidates:
        eid = a.get("eval_id")
        if eid:
            analyzed_map[eid] = a
        else:
            for tc in test_cases:
                if tc["input_signal"]["title"] == a.get("title"):
                    analyzed_map[tc["id"]] = a

    verdict_matches = 0
    total_practicality_score = 0.0
    total_specificity_score = 0.0
    case_results = []

    for c in test_cases:
        cid = c["id"]
        gt = c["ground_truth"]["analyst"]
        exp_verdict = gt["expected_verdict"]
        exp_keywords = [kw.lower() for kw in gt.get("expected_audience_keywords", [])]

        if cid in error_cases:
            err_val = error_cases[cid]
            status_val = "ERROR (fallback_used)" if "fallback_used" in str(err_val) else "ERROR"
            case_results.append({
                "id": cid,
                "title": c["input_signal"]["title"],
                "expected_verdict": exp_verdict,
                "actual_verdict": status_val,
                "status": status_val,
                "passed": False,
                "error": err_val,
                "verdict_match": False,
                "audience_text": "",
                "matched_keywords": [],
                "practicality_score": 0.0,
                "why_it_matters": ""
            })
            continue

        analyzed_item = analyzed_map.get(cid)
        if analyzed_item is None:
            # Dropped by analyst
            case_results.append({
                "id": cid,
                "title": c["input_signal"]["title"],
                "expected_verdict": exp_verdict,
                "actual_verdict": "DROPPED",
                "status": "EVALUATED",
                "passed": False,
                "verdict_match": False,
                "audience_text": "",
                "matched_keywords": [],
                "practicality_score": 0.0,
                "why_it_matters": ""
            })
            continue

        act_verdict = analyzed_item.get("verdict", "UNKNOWN")
        act_why = analyzed_item.get("why_it_matters", "")
        act_who = analyzed_item.get("who_cares", "")

        verdict_ok = (act_verdict == exp_verdict)
        if verdict_ok:
            verdict_matches += 1

        matched_kw = [kw for kw in exp_keywords if kw in act_who.lower()]
        specificity_ok = (len(matched_kw) >= 1)
        if specificity_ok:
            total_specificity_score += 1.0

        practicality = score_practicality(act_why)
        total_practicality_score += practicality

        case_passed = (verdict_ok and specificity_ok and practicality >= 3.0)

        case_results.append({
            "id": cid,
            "title": c["input_signal"]["title"],
            "expected_verdict": exp_verdict,
            "actual_verdict": act_verdict,
            "status": "EVALUATED",
            "verdict_match": verdict_ok,
            "audience_text": act_who,
            "matched_keywords": matched_kw,
            "practicality_score": practicality,
            "why_it_matters": act_why,
            "passed": case_passed
        })

    n_error = len(error_cases)
    n_evaluated = n_total - n_error

    if n_evaluated > 0:
        verdict_accuracy = (verdict_matches / n_evaluated) * 100
        audience_specificity = (total_specificity_score / n_evaluated) * 100
        avg_practicality = total_practicality_score / n_evaluated
    else:
        verdict_accuracy, audience_specificity, avg_practicality = 0.0, 0.0, 0.0

    eval_summary = {
        "node": "Analyst (Insight Practicality & Audience Specificity)",
        "n_total": n_total,
        "n_evaluated": n_evaluated,
        "n_error": n_error,
        "verdict_accuracy": round(verdict_accuracy, 1),
        "audience_specificity_rate": round(audience_specificity, 1),
        "average_practicality_score": round(avg_practicality, 2),
        "details": case_results
    }

    return eval_summary

if __name__ == "__main__":
    report = run_analyst_eval()
    print("\n" + "=" * 55)
    print("ANALYST EVALUATION REPORT:")
    print(f"Total Cases:               {report['n_total']}")
    print(f"Evaluated Cases:           {report['n_evaluated']}")
    print(f"Error Cases:               {report['n_error']}")
    print(f"Verdict Match Rate:        {report['verdict_accuracy']}%")
    print(f"Audience Specificity Rate: {report['audience_specificity_rate']}%")
    print(f"Avg Practicality (1-5):    {report['average_practicality_score']} / 5.0")
    print("=" * 55)
    for c in report["details"]:
        status = c["status"]
        pass_label = "PASS" if c["passed"] else ("ERROR" if status == "ERROR" else "FAIL")
        print(f"[{pass_label}] {c['id']}: Exp: {c['expected_verdict']} | Act: {c['actual_verdict']} | Practicality: {c['practicality_score']}/5")
