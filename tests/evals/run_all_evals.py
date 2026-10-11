import json
import logging
import sys
import time
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "backend"))

from tests.evals.eval_skeptic import run_skeptic_eval
from tests.evals.eval_verifier import run_verifier_eval
from tests.evals.eval_analyst import run_analyst_eval
from tests.evals.eval_editor import run_editor_eval


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DailyDiff.eval.runner")

def run_all_evaluations() -> dict:
    logger.info("Starting DailyDiff Complete Evaluation Suite...")
    start_time = time.time()
    
    # 1. Skeptic Node Eval
    logger.info("Executing 1/4: Skeptic Evaluation...")
    skeptic_report = run_skeptic_eval()
    
    # 2. Verifier Node Eval
    logger.info("Executing 2/4: Verifier Evaluation...")
    verifier_report = run_verifier_eval()
    
    # 3. Analyst Node Eval
    logger.info("Executing 3/4: Analyst Evaluation...")
    analyst_report = run_analyst_eval()
    
    # 4. Editor Node Eval
    logger.info("Executing 4/4: Editor Evaluation...")
    editor_report = run_editor_eval()
    
    elapsed = time.time() - start_time
    
    # Global Composite Scorecard
    total_weighted_score = (
        (skeptic_report["accuracy"] * 0.25) +
        (verifier_report["adversarial_catch_rate"] * 0.25) +
        (analyst_report["audience_specificity_rate"] * 0.25) +
        (editor_report["format_compliance_rate"] * 0.25)
    )
    
    overall_report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "benchmark_dataset": "golden_dataset.json (25 cases)",
        "total_runtime_seconds": round(elapsed, 2),
        "composite_quality_score": round(total_weighted_score, 1),
        "summary": {
            "skeptic_accuracy": skeptic_report["accuracy"],
            "skeptic_f1": skeptic_report["f1_score"],
            "skeptic_deduplication_rate": skeptic_report["deduplication_rate"],
            "verifier_accuracy": verifier_report["accuracy"],
            "verifier_adversarial_catch_rate": verifier_report["adversarial_catch_rate"],
            "verifier_false_rejection_rate": verifier_report["false_rejection_rate"],
            "analyst_verdict_accuracy": analyst_report["verdict_accuracy"],
            "analyst_audience_specificity": analyst_report["audience_specificity_rate"],
            "analyst_practicality_score": analyst_report["average_practicality_score"],
            "editor_format_compliance": editor_report["format_compliance_rate"],
            "editor_category_uniqueness": editor_report["category_uniqueness_rate"],
            "editor_readability_score": editor_report["average_readability_score"],
        },
        "nodes": {
            "skeptic": skeptic_report,
            "verifier": verifier_report,
            "analyst": analyst_report,
            "editor": editor_report
        }
    }
    
    # Save to tests/evals/eval_results.json
    results_path = BASE_DIR / "tests" / "evals" / "eval_results.json"
    with open(results_path, "w") as f:
        json.dump(overall_report, f, indent=2)
    logger.info(f"Saved complete evaluation report to {results_path}")
    
    # Also save to frontend/public for direct client loading
    frontend_public_dir = BASE_DIR / "frontend" / "public"
    frontend_public_dir.mkdir(parents=True, exist_ok=True)
    frontend_results_path = frontend_public_dir / "eval_results.json"
    with open(frontend_results_path, "w") as f:
        json.dump(overall_report, f, indent=2)
    logger.info(f"Copied evaluation report to {frontend_results_path}")
    
    return overall_report

if __name__ == "__main__":
    report = run_all_evaluations()
    print("\n" + "=" * 60)
    print("🏆 DAILYDIFF COMPOSITE EVALUATION SCORECARD")
    print(f"Overall Quality Score:       {report['composite_quality_score']}%")
    print(f"Total Benchmark Cases:       25 cases")
    print(f"Total Execution Time:        {report['total_runtime_seconds']}s")
    print("-" * 60)
    print(f"1. Skeptic Accuracy:         {report['summary']['skeptic_accuracy']}% (Dedup: {report['summary']['skeptic_deduplication_rate']}%)")
    print(f"2. Verifier Anti-Hype Rate:  {report['summary']['verifier_adversarial_catch_rate']}%")
    print(f"3. Analyst Specificity:      {report['summary']['analyst_audience_specificity']}% (Practicality: {report['summary']['analyst_practicality_score']}/5)")
    print(f"4. Editor Format Compliance: {report['summary']['editor_format_compliance']}% (Uniqueness: {report['summary']['editor_category_uniqueness']}%)")
    print("=" * 60)
