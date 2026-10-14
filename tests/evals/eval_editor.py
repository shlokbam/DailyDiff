"""
Editor evaluation fed with real Analyst outputs.
Reports quality rule checks as counts, plus DeepEval G-Eval Faithfulness per brief.
Never leaks answers from ground-truth rubric text.
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
from app.agents.editor import editor_node
from app.checks import (
    has_bold_lead, no_tldr_label, categories_unique, count_at_most_5,
    required_fields_present, category_valid, verdict_valid, url_valid_https,
    is_generic_fallback_text, unsupported_numeric_tokens
)
from app.run_health import health
from tests.evals.common import load_dataset, rate
from tests.evals.judge import create_faithfulness_geval, DailyDiffJudge, LLMTestCase

logger = logging.getLogger("DailyDiff.eval.editor")

def run_editor_eval(sample_size: int = 5, run_judge: bool = True) -> Dict[str, Any]:
    dataset = load_dataset()
    # Select sample of valid golden cases
    golden_valid = [
        c for c in dataset
        if c.get("ground_truth", {}).get("verifier", {}).get("expected_status") == "VALID"
        and c.get("ground_truth", {}).get("skeptic", {}).get("expected_decision") == "KEEP"
    ][:sample_size]

    candidates = []
    evidence_by_url = {}
    for c in golden_valid:
        sig = c["input_signal"]
        url = sig.get("url", "")
        ev = sig.get("scraped_docs", "")
        evidence_by_url[url] = ev
        candidates.append({
            "id": c["id"],
            "title": sig["title"],
            "url": url,
            "description": sig.get("raw_description", ""),
            "detailed_content": ev,
        })

    # Step 1: Run through REAL Analyst to get authentic output (never golden rubric)
    health.reset()
    analyst_out = analyst_node({"vetted_candidates": candidates})
    vetted = analyst_out.get("vetted_candidates", [])
    if not vetted:
        print("Analyst returned 0 candidates for Editor eval.")
        return {"node": "editor", "status": "ERROR", "error": "Analyst returned 0 candidates"}

    # Step 2: Feed into Editor
    health.reset()
    editor_out = editor_node({"vetted_candidates": vetted})
    briefs = editor_out.get("final_briefs") or editor_out.get("briefs", [])

    if health.has_fallbacks or health.llm_errors_count > 0:
        return {"node": "editor", "status": "ERROR", "error": "Editor LLM fallback/error"}

    total_briefs = len(briefs)
    checks_passed = {
        "bold_lead": sum(1 for b in briefs if has_bold_lead(b.get("description", ""))),
        "no_tldr": sum(1 for b in briefs if no_tldr_label(b.get("description", ""))),
        "valid_category": sum(1 for b in briefs if category_valid(b)),
        "unique_categories": total_briefs if categories_unique(briefs) else 0,
        "at_most_5": total_briefs if count_at_most_5(briefs) else 0,
        "required_fields": sum(1 for b in briefs if required_fields_present(b)),
        "https_urls": sum(1 for b in briefs if url_valid_https(b.get("source_url", ""))),
        "no_generic_text": sum(1 for b in briefs if not (is_generic_fallback_text(b.get("description", "")) or is_generic_fallback_text(b.get("why_it_matters", "")))),
        "supported_numbers": sum(1 for b in briefs if not unsupported_numeric_tokens(
            f"{b.get('title', '')} {b.get('description', '')} {b.get('why_it_matters', '')}",
            evidence_by_url.get(b.get("source_url", ""), "")
        )),
    }

    # Step 3: G-Eval Faithfulness per brief
    faithfulness_scores = []
    judge = DailyDiffJudge() if run_judge else None
    metric = create_faithfulness_geval(judge=judge) if run_judge else None

    if run_judge and metric:
        for b in briefs:
            u = b.get("source_url", "")
            ev = evidence_by_url.get(u, "")
            text = f"{b.get('title', '')}\n{b.get('description', '')}\nWhy It Matters: {b.get('why_it_matters', '')}"
            try:
                tc = LLMTestCase(input="Draft brief from evidence", actual_output=text, context=[ev[:MAX_DOC_CHARS if 'MAX_DOC_CHARS' in locals() else 3000]])
                metric.measure(tc)
                score = float(metric.score or 0.0)
                faithfulness_scores.append(score)
            except Exception as je:
                logger.warning(f"Faithfulness judge call failed for {b.get('title')}: {je}")

    avg_faith = round(sum(faithfulness_scores) / len(faithfulness_scores), 2) if faithfulness_scores else 0.0

    print(f"\n--- EDITOR EVALUATION ({total_briefs} Briefs Generated) ---")
    print("Rule Checks:")
    for chk, count in checks_passed.items():
        print(f"  {chk:22} {rate(count, total_briefs)}")
    if run_judge:
        print(f"G-Eval Faithfulness: Average = {avg_faith:.2f} ({len(faithfulness_scores)} briefs scored)")

    return {
        "node": "editor",
        "total_briefs": total_briefs,
        "rule_checks": {chk: rate(count, total_briefs) for chk, count in checks_passed.items()},
        "faithfulness_avg": avg_faith,
        "faithfulness_scores": faithfulness_scores,
    }

if __name__ == "__main__":
    run_editor_eval()
