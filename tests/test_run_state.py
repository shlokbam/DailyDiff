"""
Unit tests for backend/app/run_state.py: the per-day pipeline progress file.
"""

from app.run_state import (
    STAGES,
    new_state,
    load_state,
    save_state,
    mark_done,
    mark_failed,
    first_unfinished_stage,
    merged_outputs,
    reset_stages,
    add_rejected_urls,
    record_attempt,
)

DATE = "2026-10-21"


def test_load_missing_returns_new_state(tmp_path):
    assert load_state(tmp_path, DATE) == new_state(DATE)


def test_save_then_load_roundtrip(tmp_path):
    state = new_state(DATE)
    mark_done(state, "scout", {"raw_signals": [{"url": "https://a"}]})
    save_state(tmp_path, state)
    assert load_state(tmp_path, DATE) == state
    assert list(tmp_path.glob("*.tmp")) == []


def test_corrupt_file_starts_fresh(tmp_path):
    (tmp_path / f"{DATE}.json").write_text("{not json", encoding="utf-8")
    assert load_state(tmp_path, DATE) == new_state(DATE)


def test_other_date_ignored(tmp_path):
    old = new_state("2026-10-19")
    mark_done(old, "scout", {"raw_signals": []})
    save_state(tmp_path, old)
    assert load_state(tmp_path, DATE)["stages"] == {}


def test_first_unfinished_stage():
    state = new_state(DATE)
    assert first_unfinished_stage(state) == "scout"
    for stage in STAGES[:-1]:
        mark_done(state, stage, {})
    mark_failed(state, "editor", "429")
    assert first_unfinished_stage(state) == "editor"
    mark_done(state, "editor", {})
    assert first_unfinished_stage(state) is None


def test_merged_outputs_later_stage_wins():
    state = new_state(DATE)
    mark_done(state, "verify", {"vetted_candidates": [1]})
    mark_done(state, "analyze", {"vetted_candidates": [2]})
    mark_failed(state, "editor", "429")
    merged = merged_outputs(state)
    assert merged["vetted_candidates"] == [2]
    assert "final_briefs" not in merged


def test_reset_keeps_rejected_email_attempts():
    state = new_state(DATE)
    mark_done(state, "scout", {"raw_signals": []})
    add_rejected_urls(state, ["https://a"])
    state["email"]["status"] = "pending"
    record_attempt(state, "abc123", "verify", "too few")
    reset_stages(state)
    assert state["stages"] == {}
    assert state["rejected_urls"] == ["https://a"]
    assert state["email"]["status"] == "pending"
    assert len(state["attempts"]) == 1
    assert state["attempts"][0]["failed_stage"] == "verify"


def test_add_rejected_urls_dedupes():
    state = new_state(DATE)
    add_rejected_urls(state, ["a", "b"])
    add_rejected_urls(state, ["b", "c"])
    assert state["rejected_urls"] == ["a", "b", "c"]
