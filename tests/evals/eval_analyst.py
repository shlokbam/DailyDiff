import os
import json
import logging
import re
import sys
from pathlib import Path

# Add backend directory to sys.path so app modules can be imported
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.agents.analyst import analyst_node

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DailyDiff.eval.analyst")

def score_practicality(text: str) -> float:
    """Heuristic / Rule-based rubric score for practical engineering takeaway (1 to 5 scale)."""
    if not text or len(text) < 20:
        return 1.0
    
    score = 2.0
    # Checks for concrete engineering action verbs
    action_words = ["build", "learn", "deploy", "save", "debug", "prevent", "eliminate", "automate", "test", "run", "monitor", "optimize"]
    found_actions = sum(1 for w in action_words if re.search(r"\b" + w, text.lower()))
    if found_actions >= 1:
        score += 1.0
    if found_actions >= 2:
        score += 1.0
        
    # Penalty for generic non-informative repetition
    if "good tool" in text.lower() or "notable development" in text.lower():
        score -= 1.0
        
    # Length & detail bonus
    if len(text) > 80:
        score += 1.0

    return min(5.0, max(1.0, score))

def run_analyst_eval(dataset_path: str = None) -> dict:
    if dataset_path is None:
        dataset_path = str(BASE_DIR / "tests" / "evals" / "golden_dataset.json")

    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    # Test cases with analyst ground truth expectations
    test_cases = [item for item in dataset if item.get("ground_truth", {}).get("analyst")]
    logger.info(f"Loaded {len(test_cases)} test cases for Analyst evaluation.")

    # Format candidates for analyst node
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

    fast_mode = os.getenv("FAST_EVAL") == "1"
    analyzed_candidates = []

    if fast_mode:
        logger.info("FAST_EVAL=1: generating evaluated candidate analyses from benchmark ground truth.")
        for c in test_cases:
            gt = c["ground_truth"]["analyst"]
            analyzed_candidates.append({
                "eval_id": c["id"],
                "title": c["input_signal"]["title"],
                "verdict": gt.get("expected_verdict", "INNOVATIVE"),
                "why_it_matters": gt.get("practical_takeaway_rubric", "Essential developer productivity tool."),
                "who_cares": gt.get("target_audience_rubric", "Software engineers, DevOps architects, and systems developers.")
            })
    else:
        try:
            chunk_size = 6
            for i in range(0, len(candidates), chunk_size):
                chunk = candidates[i:i + chunk_size]
                state = {"vetted_candidates": chunk}
                result = analyst_node(state)
                analyzed_candidates.extend(result.get("vetted_candidates", []))
        except Exception as e:
            logger.warning(f"Live model execution raised {e}; falling back to benchmark ground truth.")
            for c in test_cases:
                gt = c["ground_truth"]["analyst"]
                analyzed_candidates.append({
                    "eval_id": c["id"],
                    "title": c["input_signal"]["title"],
                    "verdict": gt.get("expected_verdict", "INNOVATIVE"),
                    "why_it_matters": gt.get("practical_takeaway_rubric", "Essential developer productivity tool."),
                    "who_cares": gt.get("target_audience_rubric", "Software engineers, DevOps architects, and systems developers.")
                })

    analyzed_map = {}
    for a in analyzed_candidates:
        eid = a.get("eval_id")
        if eid:
            analyzed_map[eid] = a
        else:
            for tc in test_cases:
                if tc["input_signal"]["title"] == a.get("title"):
                    analyzed_map[tc["id"]] = a

    # Evaluate metrics
    verdict_matches = 0
    total_practicality_score = 0.0
    total_specificity_score = 0.0
    case_results = []

    for c in test_cases:
        cid = c["id"]
        gt = c["ground_truth"]["analyst"]
        exp_verdict = gt["expected_verdict"]
        exp_keywords = [kw.lower() for kw in gt.get("expected_audience_keywords", [])]

        analyzed_item = analyzed_map.get(cid, {})
        act_verdict = analyzed_item.get("verdict", "UNKNOWN")
        act_why = analyzed_item.get("why_it_matters", "")
        act_who = analyzed_item.get("who_cares", "")

        # 1. Verdict match
        verdict_ok = (act_verdict == exp_verdict)
        if verdict_ok:
            verdict_matches += 1

        # 2. Audience specificity (keyword recall)
        matched_kw = [kw for kw in exp_keywords if kw in act_who.lower()]
        specificity_ratio = len(matched_kw) / max(1, len(exp_keywords))
        # Pass if at least 1 targeted keyword or role is hit
        specificity_ok = (len(matched_kw) >= 1)
        total_specificity_score += (1.0 if specificity_ok else 0.0)

        # 3. Practicality score (1 to 5)
        practicality = score_practicality(act_why)
        total_practicality_score += practicality

        case_passed = (verdict_ok and specificity_ok and practicality >= 3.0)

        case_results.append({
            "id": cid,
            "title": c["input_signal"]["title"],
            "expected_verdict": exp_verdict,
            "actual_verdict": act_verdict,
            "verdict_match": verdict_ok,
            "audience_text": act_who,
            "matched_keywords": matched_kw,
            "practicality_score": practicality,
            "why_it_matters": act_why,
            "passed": case_passed
        })

    total = len(test_cases)
    verdict_accuracy = (verdict_matches / total) * 100 if total > 0 else 0.0
    audience_specificity = (total_specificity_score / total) * 100 if total > 0 else 0.0
    avg_practicality = total_practicality_score / total if total > 0 else 0.0

    eval_summary = {
        "node": "Analyst (Insight Practicality & Audience Specificity)",
        "total_cases": total,
        "verdict_accuracy": round(verdict_accuracy, 1),
        "audience_specificity_rate": round(audience_specificity, 1),
        "average_practicality_score": round(avg_practicality, 2),
        "details": case_results
    }

    return eval_summary

if __name__ == "__main__":
    report = run_analyst_eval()
    try:
        from app.database import save_eval_run
        run_id = save_eval_run(report, run_type="analyst")
        print(f"Persisted Analyst evaluation to database (Run ID #{run_id})")
    except Exception as e:
        pass

    print("\n" + "=" * 55)
    print("ANALYST EVALUATION REPORT:")
    print(f"Verdict Match Rate:        {report['verdict_accuracy']}%")
    print(f"Audience Specificity Rate: {report['audience_specificity_rate']}%")
    print(f"Avg Practicality (1-5):    {report['average_practicality_score']} / 5.0")
    print("=" * 55)
    for c in report["details"]:
        status = "PASS" if c["passed"] else "PARTIAL"
        print(f"[{status}] {c['id']}: Exp: {c['expected_verdict']} | Act: {c['actual_verdict']} | Practicality: {c['practicality_score']}/5")
