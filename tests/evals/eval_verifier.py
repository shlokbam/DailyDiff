"""
Verifier evaluation on golden verifier cases and planted_errors.json.
Reference-based: reports bad items caught (INVALID or UNVERIFIABLE),
good items wrongly rejected, and successful prompt injections out of 5.
"""

import logging
from typing import Dict, Any, List

from app.agents.verifier import verifier_node
from app.run_health import health
from tests.evals.common import load_dataset, load_planted_errors, rate

logger = logging.getLogger("DailyDiff.eval.verifier")

def run_verifier_eval(chunk_size: int = 5) -> Dict[str, Any]:
    golden = load_dataset()
    planted = load_planted_errors()

    all_cases = []
    for g in golden:
        exp = g["ground_truth"]["verifier"]["expected_status"]
        all_cases.append({
            "id": g["id"],
            "title": g["input_signal"]["title"],
            "description": g["input_signal"].get("raw_description", ""),
            "url": g["input_signal"].get("url", ""),
            "detailed_content": g["input_signal"].get("scraped_docs", ""),
            "content_source": "scraped_docs",
            "expected": exp,
            "is_bad": exp == "INVALID",
            "is_injection": False,
        })

    for p in planted:
        exp = p.get("expected", "INVALID")
        sig = p["input_signal"]
        all_cases.append({
            "id": p["id"],
            "title": sig["title"],
            "description": sig.get("raw_description", ""),
            "url": sig.get("url", ""),
            "detailed_content": sig.get("scraped_docs", ""),
            "content_source": sig.get("content_source", "scraped_docs"),
            "expected": exp,
            "is_bad": True,
            "is_injection": (p.get("error_type") == "prompt_injection"),
        })

    bad_total = sum(1 for c in all_cases if c["is_bad"])
    good_total = sum(1 for c in all_cases if not c["is_bad"])
    injection_total = sum(1 for c in all_cases if c["is_injection"])

    bad_caught = 0
    good_wrongly_rejected = 0
    injections_succeeded = 0
    errors = 0
    results_by_case = {}

    for i in range(0, len(all_cases), chunk_size):
        chunk = all_cases[i:i + chunk_size]
        health.reset()

        try:
            out = verifier_node({"researched_candidates": chunk})
            if health.has_fallbacks or health.llm_errors_count > 0:
                for c in chunk:
                    errors += 1
                    results_by_case[c["id"]] = {"passed": False, "status": "ERROR", "reason": "LLM fallback/error"}
                continue

            vetted_urls = {v["url"].strip().rstrip("/").lower() for v in out.get("vetted_candidates", []) if v.get("url")}

            for c in chunk:
                cid = c["id"]
                url = c["url"].strip().rstrip("/").lower()
                actual_status = "VALID" if url in vetted_urls else "REJECTED"

                passed = False
                if c["is_bad"]:
                    # Bad item is caught if it was NOT passed as VALID (marked INVALID or dropped as UNVERIFIABLE)
                    if actual_status == "REJECTED":
                        bad_caught += 1
                        passed = True
                else:
                    # Good item was expected to be VALID
                    if actual_status == "REJECTED":
                        good_wrongly_rejected += 1
                    else:
                        passed = True

                if c["is_injection"] and actual_status == "VALID":
                    injections_succeeded += 1

                results_by_case[cid] = {
                    "passed": passed,
                    "status": "PASS" if passed else "FAIL",
                    "expected": c["expected"],
                    "actual": actual_status,
                    "is_bad": c["is_bad"],
                    "is_injection": c["is_injection"],
                }

        except Exception as e:
            logger.error(f"Verifier eval exception on chunk {i}: {e}")
            for c in chunk:
                errors += 1
                results_by_case[c["id"]] = {"passed": False, "status": "ERROR", "reason": str(e)}

    bad_str = rate(bad_caught, bad_total)
    good_rej_str = rate(good_wrongly_rejected, good_total)
    inj_str = f"{injections_succeeded}/{injection_total} = {round(100.0 * injections_succeeded / injection_total if injection_total else 0)}%"

    print("\n--- VERIFIER EVALUATION (Golden + Planted Errors) ---")
    print(f"Total Cases: {len(all_cases)} (Good: {good_total}, Bad: {bad_total}, Injections: {injection_total}) | Errors: {errors}")
    print(f"Bad Items Caught (INVALID/UNVERIFIABLE): {bad_str}")
    print(f"Good Items Wrongly Rejected:            {good_rej_str}")
    print(f"Prompt Injections Succeeded:            {inj_str} (Expected: 0/{injection_total})")

    return {
        "node": "verifier",
        "total_cases": len(all_cases),
        "good_total": good_total,
        "bad_total": bad_total,
        "injection_total": injection_total,
        "bad_caught": bad_str,
        "good_wrongly_rejected": good_rej_str,
        "injections_succeeded": inj_str,
        "errors": errors,
        "cases": results_by_case,
    }

if __name__ == "__main__":
    run_verifier_eval()
