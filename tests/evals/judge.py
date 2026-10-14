"""
LLM-as-a-judge for DailyDiff evaluations using DeepEval G-Eval.
Uses real LLM calls with retry on API failure. Raises JudgeUnavailableError on failure.
Implements exactly two G-Eval metrics: Usefulness and Faithfulness.
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))

from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.metrics import GEval
try:
    from deepeval.test_case import SingleTurnParams as EvaluationParams
except ImportError:
    from deepeval.test_case import LLMTestCaseParams as EvaluationParams
from deepeval.test_case import LLMTestCase

from app.agents.models import get_llm

logger = logging.getLogger("DailyDiff.judge")

class JudgeUnavailableError(Exception):
    """Raised when the LLM judge is unavailable or fails after retries. Never fakes scores."""
    pass

class DailyDiffJudge(DeepEvalBaseLLM):
    """
    Custom DeepEval LLM Judge for DailyDiff.
    Uses the pipeline's multi-provider LLM chain.
    Retries up to 3 times on API failure with backoff; raises JudgeUnavailableError if unable to evaluate.
    """
    def __init__(self, model_name: str = "DailyDiff-Judge"):
        self.model_name = model_name
        self._llm = None

    def load_model(self):
        try:
            self._llm = get_llm(temperature=0.0)
            return self._llm
        except Exception as e:
            logger.error(f"Failed to initialize live judge LLM: {e}")
            self._llm = None
            raise JudgeUnavailableError(f"Cannot initialize judge model: {e}")

    def get_model_name(self) -> str:
        return self.model_name

    def generate(self, prompt: str, schema=None) -> str:
        is_steps_schema = False
        if schema and hasattr(schema, "model_fields") and "steps" in schema.model_fields:
            is_steps_schema = True

        last_error = None
        for attempt in range(3):
            if self._llm is None:
                self.load_model()

            try:
                response = self._llm.invoke(prompt)
                content = (getattr(response, "content", None) or str(response)).strip()

                if content.startswith("```"):
                    lines = content.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    content = "\n".join(lines).strip()

                data = json.loads(content)
                if is_steps_schema and isinstance(data, dict) and "steps" in data:
                    return json.dumps(data)
                if not is_steps_schema and isinstance(data, dict) and "score" in data:
                    return json.dumps(data)
                return json.dumps(data)

            except Exception as e:
                last_error = e
                logger.warning(f"Judge invocation attempt {attempt + 1}/3 failed: {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt)

        raise JudgeUnavailableError(f"Judge LLM failed after 3 attempts: {last_error}")

    async def a_generate(self, prompt: str, schema=None) -> str:
        return self.generate(prompt, schema)

def create_usefulness_geval(judge: Optional[DailyDiffJudge] = None, threshold: float = 0.7) -> GEval:
    """G-Eval metric measuring educational value, practical developer takeaways, and student utility."""
    return GEval(
        name="Usefulness",
        criteria=(
            "Evaluate whether the technical content provides genuine, practical utility and educational "
            "takeaways for tech students and early-career software developers, explaining what they can build, "
            "learn, or optimize, avoiding generic corporate marketing fluff."
        ),
        evaluation_params=[EvaluationParams.INPUT, EvaluationParams.ACTUAL_OUTPUT],
        model=judge or DailyDiffJudge(),
        threshold=threshold,
    )

def create_faithfulness_geval(judge: Optional[DailyDiffJudge] = None, threshold: float = 0.7) -> GEval:
    """G-Eval metric measuring whether every technical claim is grounded in the reference evidence."""
    return GEval(
        name="Faithfulness",
        criteria=(
            "Evaluate whether every technical claim, version number, benchmark, and architectural capability "
            "in the output is strictly supported by and grounded in the reference evidence documentation, "
            "with zero ungrounded assertions or hallucinated features."
        ),
        evaluation_params=[EvaluationParams.ACTUAL_OUTPUT, EvaluationParams.CONTEXT],
        model=judge or DailyDiffJudge(),
        threshold=threshold,
    )
