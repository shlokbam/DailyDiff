import pytest
from tests.evals.run_all_evals import run_all_evaluations

def test_smoke_evaluation_in_process_asserts_zero_errors():
    report = run_all_evaluations(smoke=True)
    summary = report["summary"]
    meta = report["meta"]

    assert meta["mode"] == "smoke"
    assert summary["skeptic_errors"] == 0, f"Skeptic errors: {summary['skeptic_errors']}"
    assert summary["verifier_errors"] == 0, f"Verifier errors: {summary['verifier_errors']}"
    assert summary["analyst_errors"] == 0, f"Analyst errors: {summary['analyst_errors']}"
    assert summary["editor_errors"] == 0, f"Editor errors: {summary['editor_errors']}"

    total_errors = (
        summary["skeptic_errors"]
        + summary["verifier_errors"]
        + summary["analyst_errors"]
        + summary["editor_errors"]
    )
    assert total_errors == 0, f"Total smoke errors was {total_errors}"
