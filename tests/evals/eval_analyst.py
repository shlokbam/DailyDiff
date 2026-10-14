"""
Analyst evaluation on 15 golden analyst cases.
Reference-based: verdict matches expected (WATCH, INTEGRATE, READ).
Reference-free: DeepEval G-Eval Usefulness (average score and count >= 0.7).
Note: The LLM judge is uncalibrated.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.agents.analyst import analyst_node
from app.run_health import health
from tests.evals.common import load_dataset, rate
from tests.evals.judge import create_usefulness_geval, DailyDiffJudge, LLMTestCase

logger = logging.getLogger("DailyDiff.eval.analyst")

def run_analyst_eval(chunk_size: int = 5, run_judge: bool = True) -> Dict[str, Any]:
    dataset = load_dataset()
    cases = [c for c in dataset if c.get("ground_truth", {}).get("analyst")]

    verdict_matches = 0
    errors = 0
    usefulness_scores = []
    usefulness_gte_70 = 0
    results_by_case = {}

    judge = DailyDiffJudge() if run_judge else None
    metric = create_usefulness_geval(judge=judge) if run_judge else None

    for i in range(0, len(cases), chunk_size):
        chunk = cases[i:i + chunk_size]
        candidates = []
        for c in chunk:
            sig = c["input_signal"]
            candidates.append({
                "id": c["id"],
                "title": sig["title"],
                "url": sig.get("url", ""),
                "description": sig.get("raw_description", ""),
                "detailed_content": sig.get("scraped_docs", ""),
            })

        health.reset()
        try:
            out = analyst_node({"vetted_candidates": candidates})
            if health.has_fallbacks or health.llm_errors_count > 0:
                for c in chunk:
                    errors += 1
                    results_by_case[c["id"]] = {"passed": False, "status": "ERROR", "reason": "LLM fallback/error"}
                continue

            analyzed_by_url = {cand["url"].strip().rstrip("/").lower(): cand for cand in out.get("vetted_candidates", [])}

            for c in chunk:
                cid = c["id"]
                url = c["input_signal"].get("url", "").strip().rstrip("/").lower()
                cand = analyzed_by_url.get(url)

                if not cand:
                    results_by_case[cid] = {"passed": False, "status": "DROPPED", "reason": "Dropped by Analyst"}
                    continue

                act_verdict = str(cand.get("verdict", "")).upper()
                exp_verdict = str(c["ground_truth"]["analyst"]["expected_verdict"]).upper()
                v_match = (act_verdict == exp_verdict)
                if v_match:
                    verdict_matches += 1

                score = None
                if run_judge and metric:
                    try:
                        test_case = LLMTestCase(
                            input=f"{cand['title']}: {cand.get('description', '')}\nDocs: {cand.get('detailed_content', '')[:1000]}",
                            actual_output=f"Why It Matters: {cand.get('why_it_matters', '')}\nWho Cares: {cand.get('who_cares', '')}\nVerdict: {act_verdict}",
                        )
                        metric.measure(test_case)
                        score = float(metric.score or 0.0)
                        usefulness_scores.append(score)
                        if score >= 0.7:
                            usefulness_gte_70 += 1
                    except Exception as je:
                        logger.warning(f"Judge evaluation failed for {cid}: {je}")

                results_by_case[cid] = {
                    "passed": v_match,
                    "status": "PASS" if v_match else "FAIL",
                    "expected_verdict": exp_verdict,
                    "actual_verdict": act_verdict,
                    "usefulness_score": score,
                }

        except Exception as e:
            logger.error(f"Analyst eval exception on chunk {i}: {e}")
            for c in chunk:
                errors += 1
                results_by_case[c["id"]] = {"passed": False, "status": "ERROR", "reason": str(e)}

    evaluated = len(cases) - errors
    v_rate_str = rate(verdict_matches, evaluated) if evaluated > 0 else "0/0 = 0%"
    n_scores = len(usefulness_scores)
    avg_score = round(sum(usefulness_scores) / n_scores, 2) if n_scores > 0 else 0.0
    gte_str = rate(usefulness_gte_70, n_scores) if n_scores > 0 else "0/0 = 0%"

    print("\n--- ANALYST EVALUATION (15 Golden Cases) ---")
    print(f"Total: {len(cases)} | Evaluated: {evaluated} | Errors: {errors}")
    print(f"Verdict Match (Reference-based): {v_rate_str}")
    if run_judge:
        print(f"G-Eval Usefulness (Reference-free): Average={avg_score:.2f} | Score >= 0.7: {gte_str}")
        print("  *(Note: The LLM judge is uncalibrated)*")

    return {
        "node": "analyst",
        "total_cases": len(cases),
        "evaluated": evaluated,
        "errors": errors,
        "verdict_match_rate": v_rate_str,
        "usefulness_avg": avg_score,
        "usefulness_gte_70": gte_str,
        "uncalibrated_warning": "The LLM judge is uncalibrated",
        "cases": results_by_case,
    }

if __name__ == "__main__":
    run_analyst_eval()
