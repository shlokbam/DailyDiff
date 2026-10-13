import pytest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from app.agents.models import invoke_json
from app.run_health import health

class FakeLLMSequence:
    def __init__(self, responses):
        self.responses = list(responses)
        self.call_count = 0

    def invoke(self, *args, **kwargs):
        self.call_count += 1
        resp = self.responses.pop(0)
        return AIMessage(content=resp, response_metadata={"model_name": "test-mock-model"})

def test_invoke_json_succeeds_on_second_attempt_after_malformed():
    health.reset()
    fake_llm = FakeLLMSequence([
        "Here is your answer: {not valid json",
        '```json\n[{"id": 0, "status": "VALID"}]\n```'
    ])

    result = invoke_json(
        node="verifier",
        llm=fake_llm,
        prompt="Verify these candidates",
        validate_fn=lambda x: isinstance(x, list) and len(x) == 1
    )

    assert result == [{"id": 0, "status": "VALID"}]
    assert fake_llm.call_count == 2
    assert health.has_fallbacks is False
    assert health.llm_calls_count == 2

def test_invoke_json_marks_hard_fallback_when_malformed_twice():
    health.reset()
    fake_llm = FakeLLMSequence([
        "Malformed response attempt 1",
        "Malformed response attempt 2"
    ])

    with pytest.raises(Exception):
        invoke_json(
            node="skeptic",
            llm=fake_llm,
            prompt="Filter these signals",
            validate_fn=lambda x: isinstance(x, list)
        )

    assert fake_llm.call_count == 2
    assert health.has_fallbacks is True
    assert any(f["node"] == "skeptic" for f in health.fallbacks)
    assert health.llm_calls_count == 2
