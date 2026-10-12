import json
import logging
import time
import sys
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from deepeval.models.base_model import DeepEvalBaseLLM

logger = logging.getLogger("DailyDiff.eval.deepeval_judge")

class JudgeUnavailableError(Exception):
    """Raised when the LLM judge is unavailable or fails after retries."""
    pass

class DailyDiffJudge(DeepEvalBaseLLM):
    """
    Custom DeepEval LLM Judge for DailyDiff.
    Uses real model calls with up to 3 retries and exponential backoff.
    Raises JudgeUnavailableError if the model cannot evaluate.
    Never uses simulated scores or silent fallbacks.
    """
    def __init__(self, model_name: str = "DailyDiff-Judge"):
        self.model_name = model_name
        self._llm = None

    def load_model(self):
        try:
            from app.agents.models import get_llm
            self._llm = get_llm(temperature=0.0)
            return self._llm
        except Exception as e:
            logger.error(f"Could not initialize live LLM judge client: {e}")
            self._llm = None
            return None

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

            if self._llm is None:
                raise JudgeUnavailableError("Judge LLM client could not be initialized (missing API key or provider configuration).")

            try:
                response = self._llm.invoke(prompt)
                content = response.content.strip()

                # Clean markdown JSON formatting if returned by model
                if content.startswith("```"):
                    lines = content.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    content = "\n".join(lines).strip()

                data = json.loads(content)

                if is_steps_schema:
                    if isinstance(data, dict) and "steps" in data:
                        return json.dumps(data)
                else:
                    if isinstance(data, dict) and "score" in data:
                        return json.dumps(data)

                # If JSON parsed but missing expected keys, return raw JSON string
                return json.dumps(data)

            except Exception as e:
                last_error = e
                logger.warning(f"Judge invocation attempt {attempt + 1}/3 failed: {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt)

        raise JudgeUnavailableError(f"Judge LLM unavailable after 3 retries: {last_error}")

    async def a_generate(self, prompt: str, schema=None) -> str:
        return self.generate(prompt, schema)
