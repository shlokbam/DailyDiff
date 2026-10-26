"""
Tests for retry & resume: graph start point, per-stage progress saving,
restart rules, and email wake / check / retry.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.run_state import STAGES
from app.agents.graph import create_agent_graph

NODE_FUNCS = {
    "scout": "scout_ecosystem_node",
    "skeptic": "deduplicate_and_filter_node",
    "research": "research_candidates_node",
    "verify": "verifier_node",
    "analyze": "analyst_node",
    "editor": "editor_node",
}

EMPTY_STATE = {"raw_signals": [], "candidates": [], "researched_candidates": [], "vetted_candidates": [], "final_briefs": [], "exclude_urls": []}


def test_graph_starts_at_editor_runs_only_editor():
    patches = {f"app.agents.graph.{fn}": MagicMock(side_effect=AssertionError(stage)) for stage, fn in NODE_FUNCS.items() if stage != "editor"}
    patches["app.agents.graph.editor_node"] = lambda state: {"final_briefs": ["x"]}
    with patch.multiple("app.agents.graph", **{k.rsplit(".", 1)[1]: v for k, v in patches.items()}):
        result = create_agent_graph("editor").invoke(dict(EMPTY_STATE))
    assert result["final_briefs"] == ["x"]


def test_graph_default_still_starts_at_scout():
    order = []

    def recorder(stage):
        def node(state):
            order.append(stage)
            return {"errors": []}  # langgraph 0.1.4 rejects a node update that writes nothing
        return node

    with patch.multiple("app.agents.graph", **{fn: recorder(stage) for stage, fn in NODE_FUNCS.items()}):
        create_agent_graph().invoke(dict(EMPTY_STATE))
    assert order == STAGES


def test_graph_unknown_start_raises():
    with pytest.raises(ValueError):
        create_agent_graph("nope")


# ---------------------------------------------------------------------------
# Runner: per-stage saving, stage rules, resume
# ---------------------------------------------------------------------------

import os
from datetime import datetime, timezone
from types import SimpleNamespace

from app.run_health import health
from app.run_state import load_state, save_state, new_state, mark_done, mark_failed, first_unfinished_stage
from run_agent import main as run_agent_main

CATS = ["Tech Shift", "Cool Tool", "Career & Learning", "Ecosystem Update", "Watchlist"]


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _cand(i: int) -> dict:
    return {"title": f"T{i}", "url": f"https://example.com/u{i}", "description": "d", "detailed_content": "evidence"}


def _brief(i: int) -> dict:
    return {
        "category": CATS[i % 5],
        "title": f"Tool {i}",
        "description": f"**Tool {i} is a great utility.** Useful for building software.",
        "why_it_matters": "Saves developer time.",
        "who_cares": "Engineers.",
        "verdict": "INTEGRATE",
        "source_url": f"https://example.com/u{i}",
    }


def _stages_until_editor(cands):
    return [
        ("scout", {"raw_signals": cands}),
        ("skeptic", {"candidates": cands}),
        ("research", {"researched_candidates": cands}),
        ("verify", {"vetted_candidates": cands}),
        ("analyze", {"vetted_candidates": cands}),
    ]


def _stream_graph(*chunks) -> MagicMock:
    """Fake compiled graph. Each chunk is (stage, update), or a callable run before the next chunk."""
    def stream(_input):
        for c in chunks:
            if callable(c):
                c()
                continue
            yield {c[0]: c[1]}
    graph = MagicMock()
    graph.stream.side_effect = stream
    return graph


@pytest.fixture(autouse=True)
def reset_health():
    health.reset()
    yield
    health.reset()


@pytest.fixture
def env(tmp_path):
    data = tmp_path / "data"
    (data / "archive").mkdir(parents=True)
    history = data / "history.json"
    history.write_text("[]", encoding="utf-8")
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "BACKEND_API_URL": "", "MIN_BRIEFS": "3"}), \
         patch("run_agent.init_db"), \
         patch("run_agent.DATA_DIR", data), \
         patch("run_agent.ARCHIVE_DIR", data / "archive"), \
         patch("run_agent.HISTORY_FILE_PATH", history), \
         patch("run_agent.append_to_history") as append:
        yield SimpleNamespace(state_dir=data / "runs" / "state", history=history, append=append)


def _run(graph):
    """Runs main() with the given fake graph. Returns (exit_code, graph_factory_mock)."""
    with patch("run_agent.create_agent_graph", return_value=graph) as factory:
        try:
            run_agent_main()
            code = 0
        except SystemExit as e:
            code = e.code
    return code, factory


def test_failure_stops_and_saves_progress(env):
    cands = [_cand(i) for i in range(5)]
    graph = _stream_graph(*_stages_until_editor(cands), lambda: health.mark_fallback("editor", "Error code: 429"), ("editor", {"final_briefs": []}))
    code, _ = _run(graph)
    assert code == 1
    state = load_state(env.state_dir, _today())
    for stage in ["scout", "skeptic", "research", "verify", "analyze"]:
        assert state["stages"][stage]["status"] == "done"
    assert state["stages"]["research"]["output"]["researched_candidates"] == cands
    assert state["stages"]["editor"]["status"] == "failed"
    assert "429" in state["stages"]["editor"]["reason"]
    assert len(state["attempts"]) == 1
    env.append.assert_not_called()


def test_later_steps_not_run_after_failure(env):
    cands = [_cand(i) for i in range(5)]
    chunks = _stages_until_editor(cands)
    graph = _stream_graph(*chunks[:3], lambda: health.mark_fallback("verifier", "Error code: 429"), chunks[3], chunks[4])
    code, _ = _run(graph)
    assert code == 1
    state = load_state(env.state_dir, _today())
    assert state["stages"]["verify"]["status"] == "failed"
    assert "analyze" not in state["stages"]
    assert first_unfinished_stage(state) == "verify"


def test_resume_starts_at_failed_stage(env):
    cands = [_cand(i) for i in range(5)]
    state = new_state(_today())
    for stage, update in _stages_until_editor(cands):
        mark_done(state, stage, update)
    mark_failed(state, "editor", "Error code: 429")
    save_state(env.state_dir, state)

    graph = _stream_graph(("editor", {"final_briefs": [_brief(i) for i in range(5)]}))
    code, factory = _run(graph)
    assert code == 0
    factory.assert_called_once_with("editor")
    assert graph.stream.call_args[0][0]["vetted_candidates"] == cands
    assert len(env.append.call_args[0][0]) == 5
    assert load_state(env.state_dir, _today())["stages"]["editor"]["status"] == "done"


def test_weak_verify_restarts_from_scout_with_rejected_urls(env):
    cands = [_cand(i) for i in range(1, 5)]
    graph = _stream_graph(
        ("scout", {"raw_signals": cands}),
        ("skeptic", {"candidates": cands}),
        ("research", {"researched_candidates": cands}),
        ("verify", {"vetted_candidates": cands[:1]}),
    )
    code, _ = _run(graph)
    assert code == 1
    state = load_state(env.state_dir, _today())
    rejected = [c["url"] for c in cands[1:]]
    assert state["stages"] == {}
    assert state["rejected_urls"] == rejected

    code, factory = _run(_stream_graph(("scout", {"raw_signals": []})))
    factory.assert_called_once_with("scout")
    assert factory.return_value.stream.call_args[0][0]["exclude_urls"] == rejected


def test_restart_with_nothing_new_is_not_a_quiet_day(env):
    state = new_state(_today())
    state["rejected_urls"] = ["https://example.com/u9"]
    save_state(env.state_dir, state)
    graph = _stream_graph(
        ("scout", {"raw_signals": []}),
        ("skeptic", {"candidates": []}),
        ("research", {"researched_candidates": []}),
        ("verify", {"vetted_candidates": []}),
        ("analyze", {"vetted_candidates": []}),
        ("editor", {"final_briefs": []}),
    )
    code, _ = _run(graph)
    assert code == 1
    env.append.assert_not_called()


def test_analyst_too_few_reruns_analyst(env):
    cands = [_cand(i) for i in range(5)]
    chunks = _stages_until_editor(cands)
    graph = _stream_graph(*chunks[:4], ("analyze", {"vetted_candidates": cands[:2]}))
    code, _ = _run(graph)
    assert code == 1
    state = load_state(env.state_dir, _today())
    assert state["stages"]["verify"]["status"] == "done"
    assert state["stages"]["analyze"]["status"] == "failed"
    assert first_unfinished_stage(state) == "analyze"


def test_gate_rejection_marks_editor_failed(env):
    cands = [_cand(i) for i in range(5)]
    graph = _stream_graph(*_stages_until_editor(cands), ("editor", {"final_briefs": [_brief(0), _brief(1)]}))
    code, _ = _run(graph)
    assert code == 1
    state = load_state(env.state_dir, _today())
    assert state["stages"]["editor"]["status"] == "failed"
    env.append.assert_not_called()


def test_quiet_day_still_publishes(env):
    graph = _stream_graph(
        ("scout", {"raw_signals": [_cand(1)]}),
        ("skeptic", {"candidates": []}),
        ("research", {"researched_candidates": []}),
        ("verify", {"vetted_candidates": []}),
        ("analyze", {"vetted_candidates": []}),
        ("editor", {"final_briefs": []}),
    )
    code, _ = _run(graph)
    assert code == 0
    assert env.append.call_args[0][0] == []


# ---------------------------------------------------------------------------
# Startup check and email wake / check / retry
# ---------------------------------------------------------------------------

import json
import run_agent
from run_agent import send_notification


def _resp(code: int) -> MagicMock:
    return MagicMock(status_code=code, text=f"status {code}")


def _publish_today(env, email_status=None):
    env.history.write_text(json.dumps([{"date": _today(), "published_at": "2026-10-26T03:40:00Z", "briefs": [_brief(0)]}]), encoding="utf-8")
    if email_status:
        state = new_state(_today())
        state["email"]["status"] = email_status
        save_state(env.state_dir, state)


def test_already_published_and_sent_exits_without_graph(env):
    _publish_today(env, "sent")
    with patch("run_agent.httpx.post") as post:
        code, factory = _run(MagicMock())
    assert code == 0
    factory.assert_not_called()
    post.assert_not_called()


def test_published_before_feature_exits_without_email(env):
    _publish_today(env)  # history entry, no state file
    with patch("run_agent.httpx.post") as post:
        code, factory = _run(MagicMock())
    assert code == 0
    factory.assert_not_called()
    post.assert_not_called()


def test_pending_email_is_retried_only(env):
    _publish_today(env, "pending")
    with patch.dict(os.environ, {"BACKEND_API_URL": "https://api.test"}), \
         patch("run_agent.httpx.get", return_value=_resp(200)), \
         patch("run_agent.httpx.post", return_value=_resp(200)) as post:
        code, factory = _run(MagicMock())
    assert code == 0
    post.assert_called_once()
    assert post.call_args.kwargs["json"]["date"] == _today()
    factory.assert_not_called()
    env.append.assert_not_called()
    assert load_state(env.state_dir, _today())["email"]["status"] == "sent"


def test_wake_polls_until_ready():
    with patch("run_agent.httpx.get", side_effect=[_resp(503), _resp(503), _resp(200)]) as get, \
         patch("run_agent.httpx.post", return_value=_resp(200)):
        result = send_notification("https://api.test", "tok", {"date": "d", "published_at": "p", "briefs": []}, poll_interval=0)
    assert result == (True, None)
    assert get.call_count == 3


def test_backend_never_wakes_stays_pending(env):
    with patch("run_agent.httpx.get", return_value=_resp(503)), patch("run_agent.httpx.post") as post:
        ok, msg = send_notification("https://api.test", "tok", {"date": "d", "published_at": "p", "briefs": []}, poll_interval=0, wake_timeout=0)
        assert ok is False and msg

        _publish_today(env, "pending")
        with patch.dict(os.environ, {"BACKEND_API_URL": "https://api.test"}), \
             patch("run_agent.WAKE_TIMEOUT_SECONDS", 0), patch("run_agent.WAKE_POLL_SECONDS", 0):
            code, _ = _run(MagicMock())
    assert code == 1
    post.assert_not_called()
    email = load_state(env.state_dir, _today())["email"]
    assert email["status"] == "pending"
    assert email["attempts"] == 1
    assert email["last_error"]
    env.append.assert_not_called()


def test_notify_500_is_not_success():
    with patch("run_agent.httpx.get", return_value=_resp(200)), patch("run_agent.httpx.post", return_value=_resp(500)):
        ok, msg = send_notification("https://api.test", "tok", {"date": "d", "published_at": "p", "briefs": []}, poll_interval=0)
    assert ok is False
    assert "500" in msg


def test_publish_then_email_fails_exits_1_and_keeps_pending(env):
    cands = [_cand(i) for i in range(5)]
    graph = _stream_graph(*_stages_until_editor(cands), ("editor", {"final_briefs": [_brief(i) for i in range(5)]}))
    with patch.dict(os.environ, {"BACKEND_API_URL": "https://api.test"}), \
         patch("run_agent.httpx.get", return_value=_resp(200)), \
         patch("run_agent.httpx.post", return_value=_resp(500)):
        code, _ = _run(graph)
    assert code == 1
    env.append.assert_called_once()
    assert load_state(env.state_dir, _today())["email"]["status"] == "pending"


def test_no_backend_url_marks_skipped(env):
    cands = [_cand(i) for i in range(5)]
    graph = _stream_graph(*_stages_until_editor(cands), ("editor", {"final_briefs": [_brief(i) for i in range(5)]}))
    code, _ = _run(graph)
    assert code == 0
    assert load_state(env.state_dir, _today())["email"]["status"] == "skipped"


def test_restart_flag_survives_when_verifier_rejected_nothing(env):
    """Skeptic passed 2, both VALID (< MIN_BRIEFS): restart adds no rejected URLs, but the next run must still count as a restart."""
    cands = [_cand(1), _cand(2)]
    graph = _stream_graph(
        ("scout", {"raw_signals": cands}),
        ("skeptic", {"candidates": cands}),
        ("research", {"researched_candidates": cands}),
        ("verify", {"vetted_candidates": cands}),
    )
    code, _ = _run(graph)
    assert code == 1
    assert load_state(env.state_dir, _today())["rejected_urls"] == []

    graph = _stream_graph(
        ("scout", {"raw_signals": []}),
        ("skeptic", {"candidates": []}),
        ("research", {"researched_candidates": []}),
        ("verify", {"vetted_candidates": []}),
        ("analyze", {"vetted_candidates": []}),
        ("editor", {"final_briefs": []}),
    )
    code, _ = _run(graph)
    assert code == 1
    env.append.assert_not_called()


def test_crash_after_gate_leaves_email_pending(env):
    """A crash between writing history and sending the email must not make later runs skip the email."""
    cands = [_cand(i) for i in range(5)]
    graph = _stream_graph(*_stages_until_editor(cands), ("editor", {"final_briefs": [_brief(i) for i in range(5)]}))
    with patch.dict(os.environ, {"BACKEND_API_URL": "https://api.test"}), \
         patch("run_agent.build_markdown_brief", side_effect=RuntimeError("disk full")), \
         patch("run_agent.httpx.post") as post:
        with pytest.raises(RuntimeError):
            _run(graph)
    post.assert_not_called()
    assert load_state(env.state_dir, _today())["email"]["status"] == "pending"
