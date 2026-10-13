import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.evals.live_outputs import (
    get_or_generate_live_outputs,
    get_cache_metadata,
    get_cache_file_path,
    BASE_DIR
)
from tests.evals.deepeval_adapter import build_skeptic_test_cases, get_adapter_errors

def test_429_node_error_writes_no_cache_and_adapter_returns_no_test_case(tmp_path):
    fake_cache_dir = tmp_path / ".cache"
    fake_cache_dir.mkdir()

    # Skeptic node raises a 429 error
    def failing_skeptic(state):
        raise RuntimeError("HTTP 429: Too Many Requests - rate limit exceeded")

    with patch("tests.evals.live_outputs.CACHE_DIR", fake_cache_dir):
        with patch("tests.evals.live_outputs.deduplicate_and_filter_node", side_effect=failing_skeptic):
            outputs = get_or_generate_live_outputs("skeptic")

            # Must have status ERROR
            assert len(outputs) > 0
            assert all(o["status"] == "ERROR" for o in outputs)

            # Assert NO cache file was written to disk
            cached_files = list(fake_cache_dir.glob("*.json"))
            assert len(cached_files) == 0, f"Expected 0 cache files, but found: {cached_files}"

            # Adapter must return no test cases for these error items
            with patch("tests.evals.deepeval_adapter.get_or_generate_live_outputs", return_value=outputs):
                test_cases = build_skeptic_test_cases()
                assert len(test_cases) == 0, "Adapter must return no test cases for error items"
                assert getattr(test_cases, "errors", 0) > 0, "Adapter must count errors"
                assert get_adapter_errors("skeptic") > 0

def test_changing_node_file_changes_cache_key():
    ds_path = BASE_DIR / "tests" / "evals" / "golden_dataset.json"
    meta1 = get_cache_metadata(ds_path)
    path1 = get_cache_file_path("skeptic", meta1)

    # Simulate modifying a node file by changing the code hash
    meta2 = dict(meta1)
    meta2["code_hash"] = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    path2 = get_cache_file_path("skeptic", meta2)

    assert path1.name != path2.name, f"Cache key must change when node code changes: {path1.name} vs {path2.name}"
