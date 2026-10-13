import pytest
import json
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage
from app.agents.verifier import verifier_node
from app.run_health import health
from run_agent import build_run_snapshot

def test_snapshot_records_invalid_and_unverifiable_candidates():
    health.reset()

    candidates = [
        {
            "title": "Invalid Claim Repo",
            "source": "GitHub",
            "url": "https://github.com/org/invalid",
            "description": "Claims 100x speedup with zero proof.",
            "content_source": "readme",
            "detailed_content": "A simple hello world script."
        },
        {
            "title": "Unverifiable Repo",
            "source": "GitHub",
            "url": "https://github.com/org/unverifiable",
            "description": "Claims proprietary enterprise database connection.",
            "content_source": "readme",
            "detailed_content": "No documentation provided."
        }
    ]

    mock_llm_response = [
        {"id": 0, "status": "INVALID", "reason": "Claims 100x speedup unsupported by hello world code."},
        {"id": 1, "status": "UNVERIFIABLE", "reason": "No documentation provided to verify claims."}
    ]

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content=json.dumps(mock_llm_response),
        response_metadata={"model_name": "test-mock-model"}
    )

    with patch("app.agents.verifier.get_llm", return_value=mock_llm):
        result = verifier_node({"researched_candidates": candidates})

    assert len(result["vetted_candidates"]) == 0

    # Build snapshot
    snapshot = build_run_snapshot(
        date_str="2026-10-13",
        result_state={"researched_candidates": candidates, "vetted_candidates": result["vetted_candidates"]},
        briefs=[]
    )

    assert "decisions" in snapshot
    decisions = snapshot["decisions"].get("verifier", [])
    assert len(decisions) >= 2

    invalid_decision = next((d for d in decisions if d.get("outcome") == "INVALID"), None)
    unverifiable_decision = next((d for d in decisions if d.get("outcome") == "UNVERIFIABLE"), None)

    assert invalid_decision is not None, "INVALID candidate must be present in snapshot decisions"
    assert invalid_decision.get("url") == "https://github.com/org/invalid"
    assert "Claims 100x speedup" in invalid_decision.get("reason", "")

    assert unverifiable_decision is not None, "UNVERIFIABLE candidate must be present in snapshot decisions"
    assert unverifiable_decision.get("url") == "https://github.com/org/unverifiable"
    assert "No documentation" in unverifiable_decision.get("reason", "")
