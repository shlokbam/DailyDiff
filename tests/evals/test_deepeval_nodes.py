"""
DeepEval CI/CD Test Suite for DailyDiff Pipeline Nodes
Follows the DeepEval pytest pattern:
    deepeval test run tests/evals/test_deepeval_nodes.py
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BASE_DIR / "backend") not in sys.path:
    sys.path.insert(0, str(BASE_DIR / "backend"))

import pytest
from deepeval import assert_test
from tests.evals.deepeval_judge import DailyDiffJudge
from tests.evals.deepeval_metrics import (
    create_skeptic_geval,
    create_verifier_geval,
    create_analyst_practicality_geval,
    create_analyst_audience_geval,
    create_editor_readability_geval,
)
from tests.evals.deepeval_adapter import (
    build_skeptic_test_cases,
    build_verifier_test_cases,
    build_analyst_test_cases,
    build_editor_test_cases,
)

@pytest.mark.live
def test_skeptic_node_geval():
    """DeepEval assertion evaluating Skeptic candidate relevance using G-Eval."""
    cases = build_skeptic_test_cases()
    assert getattr(cases, "errors", 0) == 0, f"DeepEval test failed due to skeptic errors: {getattr(cases, 'errors', 0)}"
    assert len(cases) > 0, "No evaluated test cases available"
    judge = DailyDiffJudge()
    metric = create_skeptic_geval(judge=judge, threshold=0.7)
    for test_case in cases[:5]:
        assert_test(test_case, [metric])

@pytest.mark.live
def test_verifier_node_geval():
    """DeepEval assertion evaluating Verifier factual groundedness against docs using G-Eval."""
    cases = build_verifier_test_cases()
    assert getattr(cases, "errors", 0) == 0, f"DeepEval test failed due to verifier errors: {getattr(cases, 'errors', 0)}"
    assert len(cases) > 0, "No evaluated test cases available"
    judge = DailyDiffJudge()
    metric = create_verifier_geval(judge=judge, threshold=0.7)
    for test_case in cases[:5]:
        assert_test(test_case, [metric])

@pytest.mark.live
def test_analyst_node_geval():
    """DeepEval assertion evaluating Analyst takeaway practicality and audience specificity using G-Eval."""
    cases = build_analyst_test_cases()
    assert getattr(cases, "errors", 0) == 0, f"DeepEval test failed due to analyst errors: {getattr(cases, 'errors', 0)}"
    assert len(cases) > 0, "No evaluated test cases available"
    judge = DailyDiffJudge()
    m_prac = create_analyst_practicality_geval(judge=judge, threshold=0.7)
    m_aud = create_analyst_audience_geval(judge=judge, threshold=0.7)
    for test_case in cases[:5]:
        assert_test(test_case, [m_prac, m_aud])

@pytest.mark.live
def test_editor_node_geval():
    """DeepEval assertion evaluating Editor ELI5 conversational tone and formatting using G-Eval."""
    cases = build_editor_test_cases()
    assert getattr(cases, "errors", 0) == 0, f"DeepEval test failed due to editor errors: {getattr(cases, 'errors', 0)}"
    assert len(cases) > 0, "No evaluated test cases available"
    judge = DailyDiffJudge()
    metric = create_editor_readability_geval(judge=judge, threshold=0.7)
    for test_case in cases[:5]:
        assert_test(test_case, [metric])
