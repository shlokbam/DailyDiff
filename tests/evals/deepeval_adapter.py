import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from deepeval.test_case import LLMTestCase

from tests.evals.live_outputs import get_or_generate_live_outputs

BASE_DIR = Path(__file__).resolve().parent.parent.parent
GOLDEN_DATASET_PATH = BASE_DIR / "tests" / "evals" / "golden_dataset.json"

ADAPTER_ERRORS: Dict[str, int] = {
    "skeptic": 0,
    "verifier": 0,
    "analyst": 0,
    "editor": 0
}

def get_adapter_errors(node_name: Optional[str] = None) -> int:
    if node_name:
        return ADAPTER_ERRORS.get(node_name, 0)
    return sum(ADAPTER_ERRORS.values())

class LLMTestCaseList(list):
    def __init__(self, items=(), errors: int = 0):
        super().__init__(items)
        self.errors = errors

def load_golden_dataset(path: Optional[str] = None) -> List[Dict[str, Any]]:
    target = path or str(GOLDEN_DATASET_PATH)
    with open(target, "r") as f:
        return json.load(f)

def build_skeptic_test_cases(dataset: Optional[List[Dict[str, Any]]] = None) -> LLMTestCaseList:
    """Convert golden dataset items into DeepEval LLMTestCase objects with REAL cached node outputs."""
    data = dataset or load_golden_dataset()
    live_outputs_list = get_or_generate_live_outputs("skeptic")
    live_map = {o["id"]: o for o in live_outputs_list}
    test_cases = []
    errors = 0

    for item in data:
        if not item.get("ground_truth", {}).get("skeptic"):
            continue
        out = live_map.get(item["id"])
        if not out or out.get("status") != "EVALUATED" or not out.get("raw_output"):
            errors += 1
            continue

        sig = item["input_signal"]
        gt = item["ground_truth"]["skeptic"]
        prompt_input = f"Title: {sig['title']}\nDescription: {sig.get('raw_description', '')}\nSource: {sig.get('source', '')}"
        expected = f"Decision: {gt['expected_decision']} | Target Relevance: {'High' if gt['is_student_relevant'] else 'Low'}"
        actual = out["raw_output"]

        test_cases.append(LLMTestCase(
            input=prompt_input,
            actual_output=actual,
            expected_output=expected,
            additional_metadata={"id": item["id"], "archetype": item.get("archetype", "")}
        ))

    ADAPTER_ERRORS["skeptic"] = errors
    return LLMTestCaseList(test_cases, errors=errors)

def build_verifier_test_cases(dataset: Optional[List[Dict[str, Any]]] = None) -> LLMTestCaseList:
    """Convert golden dataset items into DeepEval LLMTestCase objects with REAL cached node outputs."""
    data = dataset or load_golden_dataset()
    live_outputs_list = get_or_generate_live_outputs("verifier")
    live_map = {o["id"]: o for o in live_outputs_list}
    test_cases = []
    errors = 0

    for item in data:
        if not item.get("ground_truth", {}).get("verifier"):
            continue
        out = live_map.get(item["id"])
        if not out or out.get("status") != "EVALUATED" or not out.get("raw_output"):
            errors += 1
            continue

        sig = item["input_signal"]
        gt = item["ground_truth"]["verifier"]
        claim = f"Claim Summary: {sig.get('raw_description', '')}"
        doc_context = [sig.get("scraped_docs", "No documentation provided.")]
        actual = out["raw_output"]
        expected = f"Status: {gt['expected_status']}"

        test_cases.append(LLMTestCase(
            input=claim,
            actual_output=actual,
            expected_output=expected,
            context=doc_context,
            additional_metadata={"id": item["id"], "archetype": item.get("archetype", "")}
        ))

    ADAPTER_ERRORS["verifier"] = errors
    return LLMTestCaseList(test_cases, errors=errors)

def build_analyst_test_cases(dataset: Optional[List[Dict[str, Any]]] = None) -> LLMTestCaseList:
    """Convert golden dataset items into DeepEval LLMTestCase objects with REAL cached node outputs."""
    data = dataset or load_golden_dataset()
    positive_items = [i for i in data if i.get("ground_truth", {}).get("analyst")]
    live_outputs_list = get_or_generate_live_outputs("analyst")
    live_map = {o["id"]: o for o in live_outputs_list}
    test_cases = []
    errors = 0

    for item in positive_items:
        out = live_map.get(item["id"])
        if not out or out.get("status") != "EVALUATED" or not out.get("raw_output"):
            errors += 1
            continue

        sig = item["input_signal"]
        gt = item["ground_truth"]["analyst"]
        prompt_input = f"Evaluate Technology: {sig['title']}\nContext: {sig.get('raw_description', '')}"
        actual = out["raw_output"]
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

    ADAPTER_ERRORS["analyst"] = errors
    return LLMTestCaseList(test_cases, errors=errors)

def build_editor_test_cases(dataset: Optional[List[Dict[str, Any]]] = None) -> LLMTestCaseList:
    """Convert golden dataset items into DeepEval LLMTestCase objects with REAL cached node outputs."""
    editor_outputs = get_or_generate_live_outputs("editor")
    test_cases = []
    errors = 0

    for item in editor_outputs:
        if item.get("status") != "EVALUATED" or not item.get("raw_output"):
            errors += 1
            continue
        prompt_input = f"Draft Final Brief for: {item.get('title')}\nCategory: {item.get('category')}"
        actual = item.get("raw_output", "")
        expected = "Category must be developer-relevant | Must start with bold sentence | No TL;DR:"

        test_cases.append(LLMTestCase(
            input=prompt_input,
            actual_output=actual,
            expected_output=expected,
            additional_metadata={"id": item["id"], "category": item.get("category")}
        ))

    ADAPTER_ERRORS["editor"] = errors
    return LLMTestCaseList(test_cases, errors=errors)
