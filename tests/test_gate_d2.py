import os
import json
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage
from app.agents.analyst import analyst_node
from app.agents.editor import editor_node
from app.run_health import health
from run_agent import main as run_agent_main

def test_four_of_five_analyst_items_valid_produces_four_briefs_and_no_hard_fallback(tmp_path):
    health.reset()

    # 5 vetted candidates from verifier
    vetted = [
        {
            "title": f"Project {i}",
            "source": "GitHub",
            "url": f"https://github.com/org/proj{i}",
            "content_source": "readme",
            "description": f"Project {i} description",
            "detailed_content": f"Project {i} docs"
        }
        for i in range(5)
    ]

    # Analyst returns 4 items (omits item 4)
    analyst_4_items = [
        {
            "id": i,
            "why_it_matters": "Enables faster builds.",
            "who_cares": "Engineers.",
            "verdict": "INTEGRATE"
        }
        for i in range(4)
    ]

    mock_analyst_llm = MagicMock()
    mock_analyst_llm.invoke.return_value = AIMessage(
        content=json.dumps(analyst_4_items),
        response_metadata={"model_name": "test-mock-model"}
    )

    with patch("app.agents.analyst.get_llm", return_value=mock_analyst_llm):
        analyst_result = analyst_node({"vetted_candidates": vetted})

    assert len(analyst_result["vetted_candidates"]) == 4
    assert health.has_fallbacks is False, "Partial analyst drop must not trigger hard fallback"
    assert health.has_degradations is True

    # Editor receives these 4 and creates 4 briefs
    categories = ["Tech Shift", "Cool Tool", "Career & Learning", "Ecosystem Update"]
    editor_briefs = [
        {
            "category": categories[i],
            "title": f"Project {i}",
            "description": f"**Project {i} streamlines architecture.** What happened: Streamlined architecture.",
            "why_it_matters": "Enables faster builds.",
            "who_cares": "Engineers.",
            "verdict": "INTEGRATE",
            "source_url": f"https://github.com/org/proj{i}"
        }
        for i in range(4)
    ]

    mock_editor_llm = MagicMock()
    mock_editor_llm.invoke.return_value = AIMessage(
        content=json.dumps(editor_briefs),
        response_metadata={"model_name": "test-mock-model"}
    )

    with patch("app.agents.editor.get_llm", return_value=mock_editor_llm):
        editor_result = editor_node({"vetted_candidates": analyst_result["vetted_candidates"]})

    assert len(editor_result["final_briefs"]) == 4
    assert health.has_fallbacks is False

def test_verifier_drops_all_candidates_counts_as_quiet_day(tmp_path):
    health.reset()
    health.set_count("raw_signals", 10)
    health.set_count("skeptic_passed", 5)
    health.set_count("verified", 0) # Verifier dropped all

    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "raw_signals": [{"title": "T1", "url": "https://github.com/a/b"}],
        "candidates": [{"title": "T1", "url": "https://github.com/a/b"}],
        "researched_candidates": [{"title": "T1", "url": "https://github.com/a/b", "content_source": "readme", "detailed_content": "docs"}],
        "vetted_candidates": [],
        "final_briefs": []
    }

    env_overrides = {
        "GROQ_API_KEY": "test-key-mock",
        "PUBLISH_GATE": "strict",
        "MIN_BRIEFS": "3",
        "BACKEND_API_URL": "",
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
                            # Should complete quiet day without raising SystemExit(1)
                            run_agent_main()
                            assert mock_append.called, "Quiet day records empty briefs to history"
                            mock_append.assert_called_once_with([], "2026-10-13")
                            written_runs = list((fake_data / "runs").glob("*.json"))
                            assert len(written_runs) == 1
                            # Snapshot should NOT be .degraded.json
                            assert not any(".degraded." in p.name for p in written_runs)

def test_node_that_raises_is_hard_fallback(tmp_path):
    health.reset()

    class RaisingLLM:
        def invoke(self, *args, **kwargs):
            raise RuntimeError("API crash")

    mock_graph = MagicMock()
    def mock_invoke_err(state):
        state["vetted_candidates"] = [
            {"title": "P1", "url": "https://github.com/a/b", "content_source": "readme", "description": "d", "detailed_content": "c"}
        ]
        with patch("app.agents.analyst.get_llm", return_value=RaisingLLM()):
            return analyst_node(state)
    mock_graph.invoke.side_effect = mock_invoke_err

    fake_data = tmp_path / "data"
    fake_data.mkdir()

    with patch.dict(os.environ, {"PUBLISH_GATE": "strict", "GROQ_API_KEY": "test"}):
        with patch("run_agent.create_agent_graph", return_value=mock_graph):
            with patch("run_agent.DATA_DIR", fake_data):
                with patch("run_agent.append_to_history"):
                    with patch("run_agent.ARCHIVE_DIR", fake_data / "archive"):
                        with patch("run_agent.HISTORY_FILE_PATH", fake_data / "history.json"):
                            with pytest.raises(SystemExit) as exc:
                                run_agent_main()
                            assert exc.value.code == 1
                            assert health.has_fallbacks is True

def test_fewer_than_min_briefs_fails_gate(tmp_path):
    health.reset()
    health.set_count("raw_signals", 10)
    health.set_count("skeptic_passed", 5)
    health.set_count("verified", 4)

    # Only 2 briefs produced when MIN_BRIEFS is 3
    briefs = [
        {
            "category": "Tech Shift",
            "title": "T1",
            "description": "**T1 delivers primitives.** What happened: Released.",
            "why_it_matters": "Utility",
            "who_cares": "Devs",
            "verdict": "INTEGRATE",
            "source_url": "https://github.com/a/b1"
        },
        {
            "category": "Cool Tool",
            "title": "T2",
            "description": "**T2 delivers primitives.** What happened: Released.",
            "why_it_matters": "Utility",
            "who_cares": "Devs",
            "verdict": "WATCH",
            "source_url": "https://github.com/a/b2"
        }
    ]

    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "raw_signals": [{"title": b["title"], "url": b["source_url"]} for b in briefs],
        "candidates": [{"title": b["title"], "url": b["source_url"]} for b in briefs],
        "researched_candidates": [
            {"title": b["title"], "url": b["source_url"], "content_source": "readme", "detailed_content": "docs"}
            for b in briefs
        ],
        "vetted_candidates": [
            {"title": b["title"], "url": b["source_url"], "verifier_status": "VALID"}
            for b in briefs
        ],
        "final_briefs": briefs
    }

    fake_data = tmp_path / "data"
    fake_data.mkdir()

    with patch.dict(os.environ, {"PUBLISH_GATE": "strict", "MIN_BRIEFS": "3", "GROQ_API_KEY": "test"}):
        with patch("run_agent.create_agent_graph", return_value=mock_graph):
            with patch("run_agent.DATA_DIR", fake_data):
                with patch("run_agent.append_to_history"):
                    with patch("run_agent.ARCHIVE_DIR", fake_data / "archive"):
                        with patch("run_agent.HISTORY_FILE_PATH", fake_data / "history.json"):
                            with pytest.raises(SystemExit) as exc:
                                run_agent_main()
                            assert exc.value.code == 1
