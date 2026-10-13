import pytest
from app.checks import (
    unsupported_numeric_tokens,
    source_url_in_candidates,
    category_valid,
    validate_briefs,
    DESIGNATED_CATEGORIES,
)

def test_bare_version_token():
    brief = "Introducing v4 with new capabilities."
    assert "v4" in unsupported_numeric_tokens(brief, "Introducing with new capabilities.")
    assert len(unsupported_numeric_tokens(brief, "Introducing v4 with new capabilities.")) == 0

def test_multiplier_token():
    brief = "Runs 10x faster than previous iterations."
    assert "10x" in unsupported_numeric_tokens(brief, "Runs faster than previous iterations.")
    assert len(unsupported_numeric_tokens(brief, "Runs 10x faster than previous iterations.")) == 0

def test_percentage_token():
    brief = "Memory usage reduced by 40% in benchmarks."
    assert "40%" in unsupported_numeric_tokens(brief, "Memory usage reduced in benchmarks.")
    assert len(unsupported_numeric_tokens(brief, "Memory usage reduced by 40% in benchmarks.")) == 0

def test_suffix_number_token():
    brief = "Earned 250k stars on GitHub."
    assert "250k" in unsupported_numeric_tokens(brief, "Earned many stars on GitHub.")
    assert len(unsupported_numeric_tokens(brief, "Earned 250k stars on GitHub.")) == 0

def test_count_plus_token():
    brief = "Supports 280+ cloud services."
    assert "280+" in unsupported_numeric_tokens(brief, "Supports cloud services.")
    assert len(unsupported_numeric_tokens(brief, "Supports 280+ cloud services.")) == 0

def test_comma_number_normalization():
    brief = "Processed 1,000 files simultaneously."
    evidence = "Processed 1000 files simultaneously."
    assert len(unsupported_numeric_tokens(brief, evidence)) == 0

def test_source_url_in_candidates():
    candidate_urls = {"https://github.com/coollabsio/coolify"}
    valid_brief = {"source_url": "https://github.com/coollabsio/coolify/?utm_source=twitter"}
    invalid_brief = {"source_url": "https://github.com/other/repo"}

    assert source_url_in_candidates(valid_brief, candidate_urls) is True
    assert source_url_in_candidates(invalid_brief, candidate_urls) is False

def test_category_valid():
    for cat in DESIGNATED_CATEGORIES:
        assert category_valid({"category": cat}) is True

    assert category_valid({"category": "Hot Take"}) is False
    assert category_valid({"category": "Framework Update"}) is False

def test_validate_briefs_flags_invalid_source_and_category():
    brief = {
        "title": "Clean Framework",
        "category": "Hot Take",
        "description": "**Clean Framework streamlines development workflows.** What happened: Streamlined workflows.",
        "why_it_matters": "Enables faster prototyping.",
        "who_cares": "Full-stack developers.",
        "verdict": "INTEGRATE",
        "source_url": "https://github.com/unknown/repo"
    }
    candidate_urls = {"https://github.com/clean/framework"}

    violations = validate_briefs([brief], candidate_urls=candidate_urls)
    violations_text = "\n".join(violations)

    assert "invalid category 'Hot Take'" in violations_text
    assert "not in candidate URLs" in violations_text
