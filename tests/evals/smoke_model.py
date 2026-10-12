import json
from typing import Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

from tests.evals.run_meta import TRACKER

class SmokeChatModel(BaseChatModel):
    """
    Fake chat model for offline plumbing tests (--smoke mode).
    Returns valid structural responses to test graph and serialization pipelines.
    Never calls external networks or LLM APIs.
    """
    model_name: str = "fake-smoke-model"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        TRACKER.record_call("fake-smoke-model")

        # Combine message texts to inspect prompt intent
        prompt = " ".join(m.content if isinstance(m.content, str) else str(m.content) for m in messages)
        prompt_lower = prompt.lower()

        if "skeptic" in prompt_lower or "signals" in prompt_lower:
            content = "[0, 1, 2]"
        elif "verifier" in prompt_lower or "fact-check" in prompt_lower:
            content = "[0, 1]"
        elif "analyst" in prompt_lower:
            content = json.dumps([
                {
                    "id": 0,
                    "why_it_matters": "Helps developers build, learn, and test applications faster.",
                    "who_cares": "CS students building portfolios, React beginners, and software engineers",
                    "verdict": "INTEGRATE",
                    "confidence": 92
                }
            ])
        elif "editor" in prompt_lower:
            content = json.dumps([
                {
                    "title": "Smoke Development Update",
                    "description": "**Smoke Development Update provides essential developer primitives.**\n\nWhat happened: Framework primitives were structured for testing.",
                    "why_it_matters": "Enables developers to test workflows without external dependencies.",
                    "who_cares": "Developers and students",
                    "verdict": "INNOVATIVE",
                    "confidence": 90,
                    "category": "Cool Tool"
                }
            ])
        elif "steps" in prompt_lower:
            content = json.dumps({"steps": ["Step 1: Check relevance", "Step 2: Check clarity"]})
        elif "score" in prompt_lower:
            content = json.dumps({"score": 8.0, "reason": "Smoke test synthetic validation."})
        else:
            content = "{}"

        msg = AIMessage(content=content, response_metadata={"model_name": "fake-smoke-model", "model": "fake-smoke-model"})
        return ChatResult(generations=[ChatGeneration(message=msg)])

    @property
    def _llm_type(self) -> str:
        return "smoke_chat_model"
