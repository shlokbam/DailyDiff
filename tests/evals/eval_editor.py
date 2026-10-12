import os
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.agents.editor import editor_node

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DailyDiff.eval.editor")

def evaluate_brief_format(brief: dict) -> dict:
    desc = brief.get("description", "")

    # 1. Bold summary check: Must start with ** and have closing **
    starts_with_bold = desc.strip().startswith("**") and "**" in desc.strip()[2:]

    # 2. Forbidden labels check: Must NOT contain "TL;DR:"
    has_forbidden_tldr = "tl;dr:" in desc.lower()

    # 3. What happened section check
    has_what_happened = "what happened" in desc.lower() or len(desc.split("\n\n")) >= 2

    # 4. Fields completeness
    has_all_fields = all(k in brief and brief[k] for k in ["title", "description", "why_it_matters", "who_cares", "verdict", "confidence"])

    # 5. ELI5 readability heuristic: Checks for engaging, clear prose
    readability_score = 4.0
    if len(desc) < 60:
        readability_score -= 1.5
    if "as shown in equation" in desc.lower() or "asymptotically" in desc.lower():
        readability_score -= 1.0
    if starts_with_bold and not has_forbidden_tldr:
        readability_score += 1.0

    readability_score = min(5.0, max(1.0, readability_score))
    is_valid = starts_with_bold and not has_forbidden_tldr and has_all_fields

    return {
        "starts_with_bold": starts_with_bold,
        "has_forbidden_tldr": has_forbidden_tldr,
        "has_what_happened": has_what_happened,
        "has_all_fields": has_all_fields,
        "readability_score": readability_score,
        "is_valid": is_valid
    }

def run_editor_eval(dataset_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Evaluates the Editor node using real model calls.
    Never simulates or falls back to ground truth.
    On error, affected cases are marked status='ERROR' and metrics are computed only over evaluated cases.
    """
    if dataset_path is None:
        dataset_path = str(BASE_DIR / "tests" / "evals" / "golden_dataset.json")

    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    test_cases = [item for item in dataset if item.get("ground_truth", {}).get("editor")]
    n_total = len(test_cases)
    logger.info(f"Loaded {n_total} vetted candidates for Editor curation evaluation.")

    candidates = []
    for c in test_cases:
        candidates.append({
            "eval_id": c["id"],
            "title": c["input_signal"]["title"],
            "description": c["input_signal"].get("raw_description", ""),
            "why_it_matters": c["ground_truth"]["analyst"]["practical_takeaway_rubric"] if c.get("ground_truth", {}).get("analyst") else "A notable developer update.",
            "who_cares": ", ".join(c["ground_truth"]["analyst"]["expected_audience_keywords"]) if c.get("ground_truth", {}).get("analyst") else "Developers",
            "verdict": c["ground_truth"]["analyst"]["expected_verdict"] if c.get("ground_truth", {}).get("analyst") else "WATCH",
            "confidence": 90,
            "source": c["input_signal"].get("source", "GitHub"),
            "url": c["input_signal"].get("url", "")
        })

    final_briefs = []
    error_msg = None

    try:
        state = {"vetted_candidates": candidates}
        result = editor_node(state)
        final_briefs = result.get("final_briefs", [])
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Editor execution error: {error_msg}")

    case_results = []
    if error_msg:
        for c in candidates:
            case_results.append({
                "eval_id": c["eval_id"],
                "title": c["title"],
                "category": None,
                "status": "ERROR",
                "passed": False,
                "error": error_msg,
                "starts_with_bold": False,
                "has_forbidden_tldr": False,
                "readability_score": 0.0,
                "sample_snippet": ""
            })
        n_error = n_total
        n_evaluated = 0
        format_compliance = 0.0
        category_uniqueness = 0.0
        avg_readability = 0.0
        categories_used = []
    else:
        n_error = 0
        n_evaluated = len(final_briefs)
        categories = [b.get("category") for b in final_briefs]
        unique_categories = set(c for c in categories if c)
        category_uniqueness = (len(unique_categories) / len(categories)) * 100 if categories else 0.0

        format_passed_count = 0
        total_readability = 0.0

        for b in final_briefs:
            fmt = evaluate_brief_format(b)
            if fmt["is_valid"]:
                format_passed_count += 1
            total_readability += fmt["readability_score"]

            case_results.append({
                "title": b.get("title"),
                "category": b.get("category"),
                "status": "EVALUATED",
                "starts_with_bold": fmt["starts_with_bold"],
                "has_forbidden_tldr": fmt["has_forbidden_tldr"],
                "readability_score": fmt["readability_score"],
                "passed": fmt["is_valid"],
                "sample_snippet": b.get("description", "")[:120] + "..."
            })

        format_compliance = (format_passed_count / n_evaluated) * 100 if n_evaluated > 0 else 0.0
        avg_readability = total_readability / n_evaluated if n_evaluated > 0 else 0.0
        categories_used = list(unique_categories)

    eval_summary = {
        "node": "Editor (Editorial Curation, Formatting & ELI5 Tone)",
        "n_total": n_total,
        "n_evaluated": n_evaluated,
        "n_error": n_error,
        "briefs_curated": n_evaluated,
        "format_compliance_rate": round(format_compliance, 1),
        "category_uniqueness_rate": round(category_uniqueness, 1),
        "average_readability_score": round(avg_readability, 2),
        "categories_used": categories_used,
        "details": case_results
    }

    return eval_summary

if __name__ == "__main__":
    report = run_editor_eval()
    print("\n" + "=" * 55)
    print("EDITOR EVALUATION REPORT:")
    print(f"Total Input Cases:       {report['n_total']}")
    print(f"Briefs Evaluated:        {report['n_evaluated']}")
    print(f"Error Cases:             {report['n_error']}")
    print(f"Format Compliance:       {report['format_compliance_rate']}%")
    print(f"Category Uniqueness:     {report['category_uniqueness_rate']}%")
    print(f"Avg Readability (1-5):   {report['average_readability_score']} / 5.0")
    print("=" * 55)
    for c in report["details"]:
        status = c["status"]
        pass_label = "PASS" if c["passed"] else ("ERROR" if status == "ERROR" else "FAIL")
        print(f"[{pass_label}] [{c.get('category')}] {c['title'][:36]:<36} | Bold: {c.get('starts_with_bold')} | Readability: {c.get('readability_score')}/5")
