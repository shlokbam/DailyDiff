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

judge = DailyDiffJudge()

# Instantiate G-Eval Metrics
skeptic_geval = create_skeptic_geval(judge=judge, threshold=0.7)
verifier_geval = create_verifier_geval(judge=judge, threshold=0.7)
analyst_practicality_geval = create_analyst_practicality_geval(judge=judge, threshold=0.7)
analyst_audience_geval = create_analyst_audience_geval(judge=judge, threshold=0.7)
editor_readability_geval = create_editor_readability_geval(judge=judge, threshold=0.7)

# Load test cases
skeptic_cases = build_skeptic_test_cases()[:5]  # Test sample for fast CI execution
verifier_cases = build_verifier_test_cases()[:5]
analyst_cases = build_analyst_test_cases()[:5]
editor_cases = build_editor_test_cases()[:5]

@pytest.mark.parametrize("test_case", skeptic_cases)
def test_skeptic_node_geval(test_case):
    """DeepEval assertion evaluating Skeptic candidate relevance using G-Eval."""
    assert_test(test_case, [skeptic_geval])

@pytest.mark.parametrize("test_case", verifier_cases)
def test_verifier_node_geval(test_case):
    """DeepEval assertion evaluating Verifier factual groundedness against docs using G-Eval."""
    assert_test(test_case, [verifier_geval])

@pytest.mark.parametrize("test_case", analyst_cases)
def test_analyst_node_geval(test_case):
    """DeepEval assertion evaluating Analyst takeaway practicality and audience specificity using G-Eval."""
    assert_test(test_case, [analyst_practicality_geval, analyst_audience_geval])

@pytest.mark.parametrize("test_case", editor_cases)
def test_editor_node_geval(test_case):
    """DeepEval assertion evaluating Editor ELI5 conversational tone and formatting using G-Eval."""
    assert_test(test_case, [editor_readability_geval])

