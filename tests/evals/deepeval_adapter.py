import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from deepeval.test_case import LLMTestCase

from tests.evals.live_outputs import get_or_generate_live_outputs

BASE_DIR = Path(__file__).resolve().parent.parent.parent
GOLDEN_DATASET_PATH = BASE_DIR / "tests" / "evals" / "golden_dataset.json"

def load_golden_dataset(path: Optional[str] = None) -> List[Dict[str, Any]]:
    target = path or str(GOLDEN_DATASET_PATH)
    with open(target, "r") as f:
        return json.load(f)

def build_skeptic_test_cases(dataset: Optional[List[Dict[str, Any]]] = None) -> List[LLMTestCase]:
    """Convert golden dataset items into DeepEval LLMTestCase objects with REAL cached node outputs."""
    data = dataset or load_golden_dataset()
    live_outputs = {o["id"]: o["raw_output"] for o in get_or_generate_live_outputs("skeptic")}
    test_cases = []
    for item in data:
        sig = item["input_signal"]
        gt = item["ground_truth"]["skeptic"]
        prompt_input = f"Title: {sig['title']}\nDescription: {sig.get('raw_description', '')}\nSource: {sig.get('source', '')}"
        expected = f"Decision: {gt['expected_decision']} | Target Relevance: {'High' if gt['is_student_relevant'] else 'Low'}"
        actual = live_outputs.get(item["id"], "Decision: REJECT (Filtered by Skeptic)")

        test_cases.append(LLMTestCase(
            input=prompt_input,
            actual_output=actual,
            expected_output=expected,
            additional_metadata={"id": item["id"], "archetype": item.get("archetype", "")}
        ))
    return test_cases

def build_verifier_test_cases(dataset: Optional[List[Dict[str, Any]]] = None) -> List[LLMTestCase]:
    """Convert golden dataset items into DeepEval LLMTestCase objects with REAL cached node outputs."""
    data = dataset or load_golden_dataset()
    live_outputs = {o["id"]: o["raw_output"] for o in get_or_generate_live_outputs("verifier")}
    test_cases = []
    for item in data:
        sig = item["input_signal"]
        gt = item["ground_truth"]["verifier"]
        claim = f"Claim Summary: {sig.get('raw_description', '')}"
        doc_context = [sig.get("scraped_docs", "No documentation provided.")]
        actual = live_outputs.get(item["id"], "Verification Status: INVALID")
        expected = f"Status: {gt['expected_status']}"

        test_cases.append(LLMTestCase(
            input=claim,
            actual_output=actual,
            expected_output=expected,
            context=doc_context,
            additional_metadata={"id": item["id"], "archetype": item.get("archetype", "")}
        ))
    return test_cases

def build_analyst_test_cases(dataset: Optional[List[Dict[str, Any]]] = None) -> List[LLMTestCase]:
    """Convert golden dataset items into DeepEval LLMTestCase objects with REAL cached node outputs."""
    data = dataset or load_golden_dataset()
    positive_items = [i for i in data if i.get("ground_truth", {}).get("analyst")]
    live_outputs = {o["id"]: o["raw_output"] for o in get_or_generate_live_outputs("analyst")}
    test_cases = []
    for item in positive_items:
        sig = item["input_signal"]
        gt = item["ground_truth"]["analyst"]
        prompt_input = f"Evaluate Technology: {sig['title']}\nContext: {sig.get('raw_description', '')}"
        actual = live_outputs.get(item["id"], "Verdict: REJECTED\nWhy It Matters: Dropped during analysis\nWho Cares: None")
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

def build_editor_test_cases(dataset: Optional[List[Dict[str, Any]]] = None) -> List[LLMTestCase]:
    """Convert golden dataset items into DeepEval LLMTestCase objects with REAL cached node outputs."""
    editor_outputs = get_or_generate_live_outputs("editor")
    test_cases = []
    for item in editor_outputs[:5]:
        prompt_input = f"Draft Final Brief for: {item.get('title')}\nCategory: {item.get('category')}"
        actual = item.get("raw_output", "")
        expected = "Category must be developer-relevant | Must start with bold sentence | No TL;DR:"

        test_cases.append(LLMTestCase(
            input=prompt_input,
            actual_output=actual,
            expected_output=expected,
            additional_metadata={"id": item["id"], "category": item.get("category")}
        ))
    return test_cases
