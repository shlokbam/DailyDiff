"""
End-to-end pipeline evaluation on 12 frozen inputs (no network, no scout):
6 good signals, 3 should-reject signals, 3 planted-bad signals.
Reports:
- Bad items leaked into final briefs (expect 0/6)
- Rule checks on final briefs
- DeepEval G-Eval Faithfulness and Usefulness per brief
- Quality gate publishing verdict
- Operational metrics: LLM calls and latency per node
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.agents.skeptic import deduplicate_and_filter_node
from app.agents.verifier import verifier_node
from app.agents.analyst import analyst_node
from app.agents.editor import editor_node
from app.checks import categories_unique, count_at_most_5, build_evidence
from app.agents.researcher import MAX_EVIDENCE_CHARS
from app.run_health import health
from tests.evals.common import load_dataset, load_planted_errors, rate
from tests.evals.judge import create_faithfulness_geval, create_usefulness_geval, DailyDiffJudge, LLMTestCase

logger = logging.getLogger("DailyDiff.eval.pipeline")

def get_frozen_12_signals() -> List[Dict[str, Any]]:
    dataset = load_dataset()
    planted = load_planted_errors()

    good_ids = {"eval_case_001", "eval_case_002", "eval_case_003", "eval_case_004", "eval_case_006", "eval_case_010"}
    reject_ids = {"eval_case_013", "eval_case_014", "eval_case_015"}
    planted_ids = {"planted_01_exaggeration_diagrams", "planted_03_wrong_number_tanstack", "planted_09_injection_readme"}

    signals = []
    for c in dataset:
        if c["id"] in good_ids:
            s = c["input_signal"].copy()
            s["id"] = c["id"]
            s["is_bad"] = False
            s["description"] = s.get("description") or s.get("raw_description", "")
            s["scraped_docs"] = s.get("scraped_docs", "")
            signals.append(s)
        elif c["id"] in reject_ids:
            s = c["input_signal"].copy()
            s["id"] = c["id"]
            s["is_bad"] = True
            s["reject_reason"] = "should_reject_topic"
            s["description"] = s.get("description") or s.get("raw_description", "")
            s["scraped_docs"] = s.get("scraped_docs", "")
            signals.append(s)

    for p in planted:
        if p["id"] in planted_ids:
            s = p["input_signal"].copy()
            s["id"] = p["id"]
            s["is_bad"] = True
            s["reject_reason"] = p.get("error_type", "planted_bad")
            s["description"] = s.get("description") or s.get("raw_description", "")
            s["scraped_docs"] = s.get("scraped_docs", "")
            signals.append(s)

    return signals

def run_pipeline_eval(run_judge: bool = True) -> Dict[str, Any]:
    signals = get_frozen_12_signals()
    bad_urls = {s["url"].strip().rstrip("/").lower(): s for s in signals if s["is_bad"]}
    evidence_by_url = {s["url"]: build_evidence({"title": s.get("title"), "description": s.get("description") or s.get("raw_description", ""), "detailed_content": s.get("scraped_docs", "")}, MAX_EVIDENCE_CHARS) for s in signals}

    timings = {}
    llm_calls = {}

    start_total = time.time()

    # 1. Skeptic
    t0 = time.time()
    c0 = health.llm_calls_count
    with patch("app.agents.skeptic.get_published_urls", return_value=set()), patch("app.agents.skeptic.extract_history_summary", return_value="No past briefs have been published yet."):
        skeptic_out = deduplicate_and_filter_node({"raw_signals": signals})
    timings["skeptic"] = round(time.time() - t0, 2)
    llm_calls["skeptic"] = health.llm_calls_count - c0
    candidates = skeptic_out.get("candidates", [])

    # 2. Frozen Researcher (attaches stored evidence without network calls)
    t0 = time.time()
    researched = []
    for c in candidates:
        researched.append({
            "id": c.get("id"),
            "title": c.get("title"),
            "url": c.get("url"),
            "description": c.get("description") or c.get("raw_description", ""),
            "detailed_content": c.get("scraped_docs") or evidence_by_url.get(c.get("url"), ""),
            "content_source": "scraped_docs",
        })
    timings["researcher"] = round(time.time() - t0, 2)
    llm_calls["researcher"] = 0

    # 3. Verifier
    t0 = time.time()
    c0 = health.llm_calls_count
    verifier_out = verifier_node({"researched_candidates": researched})
    timings["verifier"] = round(time.time() - t0, 2)
    llm_calls["verifier"] = health.llm_calls_count - c0
    vetted = verifier_out.get("vetted_candidates", [])

    # 4. Analyst
    t0 = time.time()
    c0 = health.llm_calls_count
    analyst_out = analyst_node({"vetted_candidates": vetted})
    timings["analyst"] = round(time.time() - t0, 2)
    llm_calls["analyst"] = health.llm_calls_count - c0
    analyzed = analyst_out.get("vetted_candidates", [])

    # 5. Editor
    t0 = time.time()
    c0 = health.llm_calls_count
    editor_out = editor_node({"vetted_candidates": analyzed})
    timings["editor"] = round(time.time() - t0, 2)
    llm_calls["editor"] = health.llm_calls_count - c0
    briefs = editor_out.get("final_briefs") or editor_out.get("briefs", [])

    total_time = round(time.time() - start_total, 2)

    # Leaks detection: check if any bad item reached the final briefs
    leaked_items = []
    for b in briefs:
        u = b.get("source_url", "").strip().rstrip("/").lower()
        if u in bad_urls:
            leaked_items.append({"title": b.get("title"), "url": u, "reason": bad_urls[u].get("reject_reason")})

    from run_agent import check_briefs
    surviving, gate_failures = check_briefs(briefs, len(briefs), set(evidence_by_url.keys()), evidence_by_url, 3)
    gate_decision = "BLOCKED" if gate_failures else "WOULD PUBLISH"
    gate_reason = "; ".join(gate_failures) if gate_failures else f"{len(surviving)} valid briefs ready for publication"
    violations = [w for w in health.warnings if w.startswith("Dropped brief")]

    # DeepEval G-Eval per brief
    judge = DailyDiffJudge() if run_judge else None
    faith_metric = create_faithfulness_geval(judge=judge) if run_judge else None
    use_metric = create_usefulness_geval(judge=judge) if run_judge else None

    faith_scores = []
    use_scores = []
    if run_judge:
        for b in briefs:
            u = b.get("source_url", "")
            ev = evidence_by_url.get(u, "")
            text = f"{b.get('title', '')}\n{b.get('description', '')}\nWhy It Matters: {b.get('why_it_matters', '')}"
            try:
                tc = LLMTestCase(input="Evaluate final brief", actual_output=text, context=[ev[:3000]])
                if faith_metric:
                    faith_metric.measure(tc)
                    faith_scores.append(float(faith_metric.score or 0.0))
                if use_metric:
                    use_metric.measure(tc)
                    use_scores.append(float(use_metric.score or 0.0))
            except Exception as je:
                logger.warning(f"Judge metric evaluation failed: {je}")

    avg_faith = round(sum(faith_scores) / len(faith_scores), 2) if faith_scores else 0.0
    avg_use = round(sum(use_scores) / len(use_scores), 2) if use_scores else 0.0

    print("\n--- PIPELINE END-TO-END EVALUATION (12 Frozen Inputs) ---")
    print(f"Bad Items Leaked into Briefs: {len(leaked_items)}/6 (Expected: 0/6)")
    if leaked_items:
        for item in leaked_items:
            print(f"  WARNING - Leaked: {item['title']} ({item['reason']})")
    print(f"Gate Verdict: {gate_decision} ({gate_reason})")
    print(f"Briefs passing the gate: {len(surviving)} of {len(briefs)}")
    print(f"Final Briefs Count: {len(briefs)}")
    print(f"Rule Violations: {violations if violations else 'None (100% compliant)'}")
    if run_judge:
        print(f"G-Eval Faithfulness: Average = {avg_faith:.2f}")
        print(f"G-Eval Usefulness:   Average = {avg_use:.2f}")
    print("\nOperational Metrics:")
    for node in ["skeptic", "researcher", "verifier", "analyst", "editor"]:
        print(f"  {node:12} Calls: {llm_calls.get(node, 0)} | Time: {timings.get(node, 0.0)}s")
    print(f"  Total Duration: {total_time}s | Total LLM Calls: {sum(llm_calls.values())}")

    return {
        "node": "pipeline",
        "total_inputs": len(signals),
        "bad_items_leaked": len(leaked_items),
        "bad_items_total": 6,
        "gate_decision": gate_decision,
        "gate_reason": gate_reason,
        "briefs_count": len(briefs),
        "briefs_passing_gate": len(surviving),
        "violations": violations,
        "faithfulness_avg": avg_faith,
        "usefulness_avg": avg_use,
        "operational": {
            "timings": timings,
            "llm_calls": llm_calls,
            "total_time": total_time,
            "total_calls": sum(llm_calls.values()),
        }
    }

if __name__ == "__main__":
    run_pipeline_eval()
