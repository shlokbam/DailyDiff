import os
import json
import pytest
from unittest.mock import patch, MagicMock
from app.run_health import health
from run_agent import main as run_agent_main

def test_graph_exception_produces_degraded_snapshot_and_exit_1(tmp_path):
    health.reset()

    mock_graph = MagicMock()
    mock_graph.invoke.side_effect = RuntimeError("Catastrophic LangGraph crash")

    fake_data = tmp_path / "data"
    fake_data.mkdir()

    with patch.dict(os.environ, {"GROQ_API_KEY": "test", "PUBLISH_GATE": "strict"}):
        with patch("run_agent.create_agent_graph", return_value=mock_graph):
            with patch("run_agent.DATA_DIR", fake_data):
                with pytest.raises(SystemExit) as exc:
                    run_agent_main()
                assert exc.value.code == 1

    degraded_files = list((fake_data / "runs").glob("*.degraded.json"))
    assert len(degraded_files) == 1, "Must write DATE.degraded.json snapshot on graph exception"

    with open(degraded_files[0], "r") as f:
        snapshot = json.load(f)

    assert "failure_reasons" in snapshot
    reasons_text = " ".join(snapshot["failure_reasons"])
    assert "Catastrophic LangGraph crash" in reasons_text
    assert "health" in snapshot

def test_failed_llm_calls_do_not_record_under_unknown_model():
    health.reset()
    # Record a failed LLM call
    health.record_llm_call(node="analyst", error=RuntimeError("rate limit"))

    assert "unknown-model" not in health.models_used
    assert health.node_llm_errors.get("analyst") == 1
    assert health.llm_errors_count == 1
