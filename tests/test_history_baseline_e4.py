"""
tests/test_history_baseline_e4.py

Unit tests for published history checks baseline evaluation (E4).
Tests:
- 2026-09-04 entry fails quality checks.
- 2026-10-11 entry passes quality checks.
- Baseline file history_checks.json is correctly generated and populated.
"""

import json
from pathlib import Path
from tests.evals.eval_published_history import evaluate_day, run_history_evaluation, DEFAULT_HISTORY, DEFAULT_OUT


def test_history_dates_pass_fail():
    with open(DEFAULT_HISTORY, "r", encoding="utf-8") as f:
        history_data = json.load(f)

    by_date = {e["date"]: e for e in history_data}

    assert "2026-09-04" in by_date
    assert "2026-10-11" in by_date

    res_sep04 = evaluate_day(by_date["2026-09-04"])
    res_oct11 = evaluate_day(by_date["2026-10-11"])

    # 2026-09-04 must FAIL
    assert res_sep04["passed"] is False
    assert len(res_sep04["violations"]) > 0

    # 2026-10-11 must PASS
    assert res_oct11["passed"] is True
    assert len(res_oct11["violations"]) == 0


def test_baseline_json_generation(tmp_path):
    out_file = tmp_path / "test_history_checks.json"
    result = run_history_evaluation(DEFAULT_HISTORY, Path(tmp_path / "nonexistent_runs"), out_file)

    assert out_file.exists()
    assert "windows" in result
    assert "per_date" in result
    assert result["metadata"]["skipped_checks"] == ["evidence_based_numeric_tokens"]

    # Verify 2026-09-04 and 2026-10-11 in per_date results
    per_date_map = {d["date"]: d for d in result["per_date"]}
    assert per_date_map["2026-09-04"]["passed"] is False
    assert per_date_map["2026-10-11"]["passed"] is True
