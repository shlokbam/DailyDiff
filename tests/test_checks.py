import json
from pathlib import Path
import pytest
from app.checks import (
    has_bold_lead,
    no_tldr_label,
    categories_unique,
    count_at_most_5,
    verdict_valid,
    required_fields_present,
    url_valid_https,
    is_generic_fallback_text,
    unsupported_numeric_tokens,
    validate_briefs,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
HISTORY_FILE = ROOT_DIR / "data" / "history.json"

@pytest.fixture(scope="module")
def history_data():
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def test_generic_fallback_text_matches_both_patterns():
    pattern1 = "A new open source development in the Hacker News ecosystem."
    pattern2 = "A notable new development in the GitHub ecosystem."
    non_fallback = "TanStack Router provides type-safe client-side routing for modern applications."

    assert is_generic_fallback_text(pattern1) is True
    assert is_generic_fallback_text(pattern2) is True
    assert is_generic_fallback_text(non_fallback) is False

def test_unsupported_numeric_tokens():
    brief = "We launched Coolify v4.2 and Coolify 3.0 today."
    evidence = "Coolify is a self-hosting platform with release v4.2."

    unsupported = unsupported_numeric_tokens(brief, evidence)
    assert "3.0" in unsupported
    assert "v4.2" not in unsupported

def test_history_fixture_2026_09_04_produces_violations(history_data):
    entry = next((d for d in history_data if d.get("date") == "2026-09-04"), None)
    assert entry is not None, "2026-09-04 entry must exist in data/history.json"

    briefs = entry.get("briefs", [])
    violations = validate_briefs(briefs)

    assert len(violations) > 0, "2026-09-04 degraded run must produce violations"
    violations_text = "\n".join(violations)

    # Must flag bold lead missing, duplicate category, and generic fallback text
    assert "missing prepended bold lead-in" in violations_text
    assert "Category uniqueness violation" in violations_text
    assert "generic fallback text" in violations_text

def test_history_fixture_2026_10_11_passes_cleanly(history_data):
    entry = next((d for d in history_data if d.get("date") == "2026-10-11"), None)
    assert entry is not None, "2026-10-11 entry must exist in data/history.json"

    briefs = entry.get("briefs", [])
    violations = validate_briefs(briefs)

    assert len(violations) == 0, f"2026-10-11 normal run must pass with 0 violations, got: {violations}"
