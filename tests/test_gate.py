"""
Unit tests for the publication gate in backend/run_agent.py.
Verifies fail-closed behavior, degraded snapshot creation, quiet days,
and history integrity without depending on a hardcoded date.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

from app.run_health import health
from run_agent import main as run_agent_main, check_briefs


@pytest.fixture(autouse=True)
def reset_health():
    health.reset()
    yield
    health.reset()


@pytest.fixture(autouse=True)
def mock_db():
    with patch("run_agent.init_db"):
        yield



def _make_brief(i: int, cat: str = "Tech Shift") -> dict:
    return {
        "category": cat,
        "title": f"Tool {i}",
        "description": f"**Tool {i} is a great utility.** Useful for building software.",
        "why_it_matters": "Saves developer time.",
        "who_cares": "Engineers.",
        "verdict": "INTEGRATE",
        "source_url": f"https://github.com/example/tool_{i}",
    }


def test_gate_blocks_on_hard_failure(tmp_path):
    """If any node records a hard failure, the gate must exit 1, write degraded snapshot, and leave history untouched."""
    fake_data = tmp_path / "data"
    fake_data.mkdir()
    fake_archive = fake_data / "archive"
    fake_archive.mkdir()
    fake_history = fake_data / "history.json"
    fake_history.write_text("[]", encoding="utf-8")

    def failing_invoke(state):
        health.mark_fallback("verifier", "Model 429 rate limit")
        return {
            "raw_signals": [{"title": "T1", "url": "https://github.com/example/tool_1"}],
            "candidates": [],
            "researched_candidates": [],
            "vetted_candidates": [],
            "final_briefs": [_make_brief(1), _make_brief(2), _make_brief(3)],
        }

    mock_graph = MagicMock()
    mock_graph.invoke.side_effect = failing_invoke

    env_overrides = {
        "GROQ_API_KEY": "test-key",
        "BACKEND_API_URL": "",
        "MIN_BRIEFS": "3",
    }

    with patch.dict(os.environ, env_overrides):
        with patch("run_agent.create_agent_graph", return_value=mock_graph):
            with patch("run_agent.append_to_history") as mock_append:
                with patch("run_agent.DATA_DIR", fake_data):
                    with patch("run_agent.ARCHIVE_DIR", fake_archive):
                        with patch("run_agent.HISTORY_FILE_PATH", fake_history):
                            with pytest.raises(SystemExit) as exc_info:
                                run_agent_main()
                            assert exc_info.value.code == 1

                            # History must NOT be touched
                            mock_append.assert_not_called()
                            assert fake_history.read_text(encoding="utf-8") == "[]"

                            # Degraded snapshot must be written
                            runs_dir = fake_data / "runs"
                            assert runs_dir.exists()
                            degraded_files = list(runs_dir.glob("*.degraded.json"))
                            assert len(degraded_files) == 1
                            snapshot = json.loads(degraded_files[0].read_text(encoding="utf-8"))
                            assert len(snapshot.get("failure_reasons", [])) > 0


def test_gate_publishes_when_one_item_dropped(tmp_path):
    """If 4 of 5 briefs survive rule checks with no hard failure, gate publishes successfully."""
    cats = ["Tech Shift", "Cool Tool", "Career & Learning", "Ecosystem Update", "Watchlist"]
    valid_briefs = [_make_brief(i, cats[i]) for i in range(4)]
    bad_brief = _make_brief(5, "InvalidCategory")  # will be dropped by quality checks

    fake_data = tmp_path / "data"
    fake_data.mkdir()
    fake_archive = fake_data / "archive"
    fake_archive.mkdir()
    fake_history = fake_data / "history.json"
    fake_history.write_text("[]", encoding="utf-8")

    all_briefs = valid_briefs + [bad_brief]
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "raw_signals": [{"title": f"T{i}", "url": b["source_url"]} for i, b in enumerate(all_briefs)],
        "candidates": [{"title": f"T{i}", "url": b["source_url"]} for i, b in enumerate(all_briefs)],
        "researched_candidates": [{"title": f"T{i}", "url": b["source_url"]} for i, b in enumerate(all_briefs)],
        "vetted_candidates": [{"title": f"T{i}", "url": b["source_url"]} for i, b in enumerate(all_briefs)],
        "final_briefs": all_briefs,
    }

    env_overrides = {
        "GROQ_API_KEY": "test-key",
        "BACKEND_API_URL": "",
        "MIN_BRIEFS": "3",
    }

    with patch.dict(os.environ, env_overrides):
        with patch("run_agent.create_agent_graph", return_value=mock_graph):
            with patch("run_agent.append_to_history") as mock_append:
                with patch("run_agent.DATA_DIR", fake_data):
                    with patch("run_agent.ARCHIVE_DIR", fake_archive):
                        with patch("run_agent.HISTORY_FILE_PATH", fake_history):
                            run_agent_main()
                            assert mock_append.called
                            published_briefs = mock_append.call_args[0][0]
                            assert len(published_briefs) == 4

                            # Normal run snapshot written
                            runs_dir = fake_data / "runs"
                            run_files = [f for f in runs_dir.glob("*.json") if not f.name.endswith(".degraded.json")]
                            assert len(run_files) == 1


def test_quiet_day_publishes(tmp_path):
    """A genuine quiet day (zero candidates survived legitimately, no hard failures) publishes empty list."""
    fake_data = tmp_path / "data"
    fake_data.mkdir()
    fake_archive = fake_data / "archive"
    fake_archive.mkdir()
    fake_history = fake_data / "history.json"
    fake_history.write_text("[]", encoding="utf-8")

    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "raw_signals": [{"title": "T1", "url": "https://github.com/example/tool_1"}],
        "candidates": [],
        "researched_candidates": [],
        "vetted_candidates": [],
        "final_briefs": [],
    }

    env_overrides = {
        "GROQ_API_KEY": "test-key",
        "BACKEND_API_URL": "",
        "MIN_BRIEFS": "3",
    }

    with patch.dict(os.environ, env_overrides):
        with patch("run_agent.create_agent_graph", return_value=mock_graph):
            with patch("run_agent.append_to_history") as mock_append:
                with patch("run_agent.DATA_DIR", fake_data):
                    with patch("run_agent.ARCHIVE_DIR", fake_archive):
                        with patch("run_agent.HISTORY_FILE_PATH", fake_history):
                            run_agent_main()
                            assert mock_append.called
                            assert mock_append.call_args[0][0] == []


def test_fewer_than_min_briefs_blocks(tmp_path):
    """When fewer than MIN_BRIEFS survive and it is NOT a quiet day, gate blocks and exits 1."""
    cats = ["Tech Shift", "Cool Tool"]
    two_briefs = [_make_brief(i, cats[i]) for i in range(2)]

    fake_data = tmp_path / "data"
    fake_data.mkdir()
    fake_archive = fake_data / "archive"
    fake_archive.mkdir()
    fake_history = fake_data / "history.json"
    fake_history.write_text("[]", encoding="utf-8")

    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "raw_signals": [{"title": "T1", "url": "https://github.com/example/tool_1"}],
        "candidates": [{"title": "T1", "url": "https://github.com/example/tool_1"}],
        "researched_candidates": [{"title": "T1", "url": "https://github.com/example/tool_1"}],
        "vetted_candidates": [{"title": "T1", "url": "https://github.com/example/tool_1"}],
        "final_briefs": two_briefs,  # only 2 briefs, MIN_BRIEFS defaults to 3
    }

    env_overrides = {
        "GROQ_API_KEY": "test-key",
        "BACKEND_API_URL": "",
        "MIN_BRIEFS": "3",
    }

    with patch.dict(os.environ, env_overrides):
        with patch("run_agent.create_agent_graph", return_value=mock_graph):
            with patch("run_agent.append_to_history") as mock_append:
                with patch("run_agent.DATA_DIR", fake_data):
                    with patch("run_agent.ARCHIVE_DIR", fake_archive):
                        with patch("run_agent.HISTORY_FILE_PATH", fake_history):
                            with pytest.raises(SystemExit) as exc_info:
                                run_agent_main()
                            assert exc_info.value.code == 1
                            mock_append.assert_not_called()


def test_all_briefs_dropped_is_blocked_not_a_quiet_day():
    briefs = [
        {
            "category": "Tech Shift",
            "title": f"Tool {i}",
            "description": "No bold lead sentence here.",
            "why_it_matters": "Why.",
            "who_cares": "Who.",
            "verdict": "READ",
            "source_url": f"https://example.com/tool_{i}",
        }
        for i in range(5)
    ]
    candidate_urls = {b["source_url"] for b in briefs}
    surviving, reasons = check_briefs(briefs, produced_count=5, candidate_urls=candidate_urls, evidence_by_url={}, min_briefs=3)
    assert surviving == []
    assert any("dropped" in r for r in reasons)


def test_zero_produced_and_healthy_is_a_quiet_day():
    surviving, reasons = check_briefs([], produced_count=0, candidate_urls=set(), evidence_by_url={}, min_briefs=3)
    assert reasons == []


def test_zero_produced_with_llm_error_is_blocked():
    health.record_llm_call("editor", error=RuntimeError("x"))
    surviving, reasons = check_briefs([], produced_count=0, candidate_urls=set(), evidence_by_url={}, min_briefs=3)
    assert len(reasons) > 0

