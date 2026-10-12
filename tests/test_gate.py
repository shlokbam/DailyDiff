import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage

from app.run_health import health
from app.agents.models import invoke_llm, BudgetExceeded
from app.agents.verifier import verifier_node
from app.agents.analyst import analyst_node
from app.agents.editor import editor_node
from app.agents.skeptic import deduplicate_and_filter_node
from run_agent import main as run_agent_main

class Mock429Error(Exception):
    """Simulated HTTP 429 Rate Limit error."""
    pass

class FailingLLM:
    def invoke(self, *args, **kwargs):
        raise Mock429Error("HTTP 429: Too Many Requests / Rate limit exceeded")

def test_budget_exceeded_raises():
    health.reset()
    mock_llm = MagicMock()
    with patch.dict(os.environ, {"LLM_TIME_BUDGET_SECONDS": "0"}):
        # Force health.over_budget() to True
        with patch.object(health, "over_budget", return_value=True):
            with pytest.raises(BudgetExceeded):
                invoke_llm("test_node", mock_llm, "test prompt")

def test_skeptic_fails_closed_on_429():
    health.reset()
    state = {
        "raw_signals": [
            {"source": "GitHub", "title": "Cool Repo", "url": "https://github.com/a/b", "description": "A repo."}
        ]
    }
    with patch("app.agents.skeptic.get_llm", return_value=FailingLLM()):
        with patch("app.agents.skeptic.get_published_urls", return_value=set()):
            result = deduplicate_and_filter_node(state)
            assert result["candidates"] == [], "Skeptic must return empty list on LLM failure"
            assert health.has_fallbacks is True
            assert any(f["node"] == "skeptic" for f in health.fallbacks)

def test_verifier_fails_closed_on_429():
    health.reset()
    state = {
        "researched_candidates": [
            {
                "title": "TanStack Router",
                "source": "GitHub",
                "url": "https://github.com/tanstack/router",
                "content_source": "readme",
                "detailed_content": "Type-safe routing for modern applications.",
                "description": "TanStack Router is a type-safe routing library."
            }
        ]
    }
    with patch("app.agents.verifier.get_llm", return_value=FailingLLM()):
        result = verifier_node(state)
        assert result["vetted_candidates"] == [], "Verifier must return empty list on LLM failure"
        assert health.has_fallbacks is True
        assert any(f["node"] == "verifier" for f in health.fallbacks)

def test_analyst_fails_closed_on_429():
    health.reset()
    state = {
        "vetted_candidates": [
            {
                "title": "Immich",
                "source": "GitHub",
                "url": "https://github.com/immich-app/immich",
                "content_source": "readme",
                "detailed_content": "Self-hosted photo management.",
                "description": "Immich is a high-performance self-hosted photos platform."
            }
        ]
    }
    with patch("app.agents.analyst.get_llm", return_value=FailingLLM()):
        result = analyst_node(state)
        assert result["vetted_candidates"] == [], "Analyst must return empty list on LLM failure"
        assert health.has_fallbacks is True
        assert any(f["node"] == "analyst" for f in health.fallbacks)

def test_editor_fails_closed_on_429():
    health.reset()
    state = {
        "vetted_candidates": [
            {
                "title": "Coolify",
                "source": "GitHub",
                "url": "https://github.com/coollabsio/coolify",
                "content_source": "readme",
                "detailed_content": "An open-source self-hosting solution.",
                "description": "Coolify is an open-source self-hosting dashboard.",
                "why_it_matters": "Simplifies server management.",
                "who_cares": "Developers hosting apps.",
                "verdict": "INTEGRATE"
            }
        ]
    }
    with patch("app.agents.editor.get_llm", return_value=FailingLLM()):
        result = editor_node(state)
        assert result["final_briefs"] == [], "Editor must return empty list on LLM failure"
        assert health.has_fallbacks is True
        assert any(f["node"] == "editor" for f in health.fallbacks)

def test_gate_degraded_state_blocks_publication(tmp_path):
    mock_graph = MagicMock()
    def mock_invoke(state):
        health.mark_fallback("verifier", "HTTP 429 Rate limit exceeded")
        return {
            "raw_signals": [],
            "candidates": [],
            "researched_candidates": [],
            "vetted_candidates": [],
            "final_briefs": []
        }
    mock_graph.invoke.side_effect = mock_invoke

    env_overrides = {
        "GROQ_API_KEY": "test-key-mock",
        "BACKEND_API_URL": "http://mock-backend:8000",
        "PUBLISH_GATE": "strict",
    }

    fake_data = tmp_path / "data"
    fake_data.mkdir()

    with patch.dict(os.environ, env_overrides):
        with patch("run_agent.create_agent_graph", return_value=mock_graph):
            with patch("run_agent.append_to_history") as mock_append:
                with patch("run_agent.DATA_DIR", fake_data):
                    with patch("httpx.post") as mock_http:
                        with pytest.raises(SystemExit) as exc_info:
                            run_agent_main()
                        assert exc_info.value.code == 1, "Degraded pipeline must exit with code 1"
                        assert not mock_append.called, "append_to_history must NOT be called on degraded run"
                        assert not mock_http.called, "Notify webhook must NOT be called on degraded run"
                        # Verify degraded snapshot was written to fake_data/runs
                        written_degraded = list((fake_data / "runs").glob("*.degraded.json"))
                        assert len(written_degraded) == 1

def test_gate_healthy_state_publishes(tmp_path):
    health.reset()
    valid_briefs = [
        {
            "category": "Cool Tool",
            "title": "Diagrams as Code in Python",
            "description": "**You can now generate cloud architecture diagrams using plain Python code.** Diagrams lets you sketch system topologies.",
            "why_it_matters": "Treating diagrams as code lets you version-control architecture alongside source repositories.",
            "who_cares": "Backend engineers and DevOps architects.",
            "verdict": "INTEGRATE",
            "source_url": "https://github.com/mingrammer/diagrams"
        }
    ]

    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "raw_signals": [{"title": "Diagrams", "url": "https://github.com/mingrammer/diagrams", "source": "GitHub", "description": "Diagrams as code"}],
        "candidates": [{"title": "Diagrams", "url": "https://github.com/mingrammer/diagrams"}],
        "researched_candidates": [{
            "title": "Diagrams",
            "url": "https://github.com/mingrammer/diagrams",
            "source": "GitHub",
            "content_source": "readme",
            "description": "Diagrams as code",
            "detailed_content": "Diagrams lets you draw cloud architecture using python code."
        }],
        "vetted_candidates": [{
            "title": "Diagrams",
            "url": "https://github.com/mingrammer/diagrams",
            "verifier_status": "VALID",
            "verifier_reason": "Verified against README",
            "verdict": "INTEGRATE",
            "why_it_matters": "Version controlled diagrams.",
            "who_cares": "DevOps developers"
        }],
        "final_briefs": valid_briefs
    }

    env_overrides = {
        "GROQ_API_KEY": "test-key-mock",
        "PUBLISH_GATE": "strict",
        "BACKEND_API_URL": "",  # Don't call webhook in unit test
    }

    fake_data = tmp_path / "data"
    fake_data.mkdir()
    fake_archive = fake_data / "archive"
    fake_archive.mkdir()
    fake_history = fake_data / "history.json"

    with patch.dict(os.environ, env_overrides):
        with patch("run_agent.create_agent_graph", return_value=mock_graph):
            with patch("run_agent.append_to_history") as mock_append:
                with patch("run_agent.DATA_DIR", fake_data):
                    with patch("run_agent.ARCHIVE_DIR", fake_archive):
                        with patch("run_agent.HISTORY_FILE_PATH", fake_history):
                            run_agent_main()
                            assert mock_append.called, "append_to_history MUST be called on healthy run"
                            written_runs = list((fake_data / "runs").glob("*.json"))
                            assert len(written_runs) == 1
                            assert not any(".degraded." in p.name for p in written_runs)
