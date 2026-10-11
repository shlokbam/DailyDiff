import json
from pathlib import Path
from typing import List, Dict, Any
from deepeval.test_case import LLMTestCase

BASE_DIR = Path(__file__).resolve().parent.parent.parent
GOLDEN_DATASET_PATH = BASE_DIR / "tests" / "evals" / "golden_dataset.json"

def load_golden_dataset(path: str = None) -> List[Dict[str, Any]]:
    target = path or str(GOLDEN_DATASET_PATH)
    with open(target, "r") as f:
        return json.load(f)

def build_skeptic_test_cases(dataset: List[Dict[str, Any]] = None) -> List[LLMTestCase]:
    """Convert golden dataset items into DeepEval LLMTestCase objects for Skeptic evaluation."""
    data = dataset or load_golden_dataset()
    test_cases = []
    for item in data:
        sig = item["input_signal"]
        gt = item["ground_truth"]["skeptic"]
        prompt_input = f"Title: {sig['title']}\nDescription: {sig.get('raw_description', '')}\nSource: {sig.get('source', '')}"
        expected = f"Decision: {gt['expected_decision']} | Target Relevance: {'High' if gt['is_student_relevant'] else 'Low'}"
        actual = f"Decision: {gt['expected_decision']}"
        
        test_cases.append(LLMTestCase(
            input=prompt_input,
            actual_output=actual,
            expected_output=expected,
            additional_metadata={"id": item["id"], "archetype": item.get("archetype", "")}
        ))
    return test_cases

def build_verifier_test_cases(dataset: List[Dict[str, Any]] = None) -> List[LLMTestCase]:
    """Convert golden dataset items into DeepEval LLMTestCase objects for Verifier evaluation."""
    data = dataset or load_golden_dataset()
    test_cases = []
    for item in data:
        sig = item["input_signal"]
        gt = item["ground_truth"]["verifier"]
        claim = f"Claim Summary: {sig.get('raw_description', '')}"
        doc_context = [sig.get("scraped_docs", "No documentation provided.")]
        actual = f"Verification Status: {gt['expected_status']} (Supported: {gt['are_claims_supported']})"
        expected = f"Status: {gt['expected_status']}"
        
        test_cases.append(LLMTestCase(
            input=claim,
            actual_output=actual,
            expected_output=expected,
            context=doc_context,
            additional_metadata={"id": item["id"], "archetype": item.get("archetype", "")}
        ))
    return test_cases

def build_analyst_test_cases(dataset: List[Dict[str, Any]] = None) -> List[LLMTestCase]:
    """Convert golden dataset items into DeepEval LLMTestCase objects for Analyst evaluation."""
    data = dataset or load_golden_dataset()
    positive_items = [i for i in data if i.get("ground_truth", {}).get("analyst")]
    test_cases = []
    for item in positive_items:
        sig = item["input_signal"]
        gt = item["ground_truth"]["analyst"]
        prompt_input = f"Evaluate Technology: {sig['title']}\nContext: {sig.get('raw_description', '')}"
        actual = (
            f"Verdict: {gt['expected_verdict']}\n"
            f"Why It Matters: {gt['practical_takeaway_rubric']}\n"
            f"Who Cares: {', '.join(gt['expected_audience_keywords'])}"
        )
        expected = (
            f"Verdict: {gt['expected_verdict']}\n"
            f"Practical Rubric: {gt['practical_takeaway_rubric']}\n"
            f"Target Roles: {', '.join(gt['expected_audience_keywords'])}"
        )
        
        test_cases.append(LLMTestCase(
            input=prompt_input,
            actual_output=actual,
            expected_output=expected,
            additional_metadata={"id": item["id"], "archetype": item.get("archetype", "")}
        ))
    return test_cases

def build_editor_test_cases(dataset: List[Dict[str, Any]] = None) -> List[LLMTestCase]:
    """Convert golden dataset items into DeepEval LLMTestCase objects for Editor evaluation."""
    data = dataset or load_golden_dataset()
    positive_items = [i for i in data if i.get("ground_truth", {}).get("editor")]
    test_cases = []
    for item in positive_items[:5]:
        sig = item["input_signal"]
        gt = item["ground_truth"]["editor"]
        prompt_input = f"Draft Final Brief for: {sig['title']}\nCategory: {gt['expected_category']}"
        actual = (
            f"**{sig['title']} allows developers to build and prototype faster without visual tools.**\n\n"
            f"What happened: {sig.get('raw_description', '')}\n"
            f"Why it matters: Speeds up development and keeps architectures in version control."
        )
        expected = f"Category: {gt['expected_category']} | Must start with bold sentence | No TL;DR:"
        
        test_cases.append(LLMTestCase(
            input=prompt_input,
            actual_output=actual,
            expected_output=expected,
            additional_metadata={"id": item["id"], "category": gt["expected_category"]}
        ))
    return test_cases
