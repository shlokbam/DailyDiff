"""
Unit tests for backend/app/checks.py quality rules.
Covers each rule check with at least one good and one bad example.
"""

import json
from pathlib import Path
import pytest

from app.checks import (
    has_bold_lead,
    no_tldr_label,
    categories_unique,
    count_at_most_5,
    verdict_valid,
    category_valid,
    required_fields_present,
    url_valid_https,
    normalize_url,
    source_url_in_candidates,
    is_generic_fallback_text,
    unsupported_numeric_tokens,
    validate_briefs,
    DESIGNATED_CATEGORIES,
    build_evidence,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
HISTORY_FILE = ROOT_DIR / "data" / "history.json"


# 1. Bold lead sentence
def test_has_bold_lead():
    good = "**TanStack Router brings type-safe routing to React.** Full description follows."
    bad = "TanStack Router brings type-safe routing to React without bold lead."
    assert has_bold_lead(good) is True
    assert has_bold_lead(bad) is False
    assert has_bold_lead("") is False


# 2. No TL;DR label
def test_no_tldr_label():
    good = "**Fast SQLite client.** Optimized for microservices."
    bad1 = "**TL;DR:** Fast SQLite client."
    bad2 = "**tldr:** Fast SQLite client."
    assert no_tldr_label(good) is True
    assert no_tldr_label(bad1) is False
    assert no_tldr_label(bad2) is False


# 3. Category validity
def test_category_valid():
    for cat in DESIGNATED_CATEGORIES:
        assert category_valid({"category": cat}) is True
    assert category_valid({"category": "Random Category"}) is False
    assert category_valid({"category": ""}) is False


# 4. Categories uniqueness
def test_categories_unique():
    good = [{"category": "Tech Shift"}, {"category": "Cool Tool"}]
    bad = [{"category": "Tech Shift"}, {"category": "Tech Shift"}]
    assert categories_unique(good) is True
    assert categories_unique(bad) is False


# 5. Count at most 5 briefs
def test_count_at_most_5():
    assert count_at_most_5([{"category": "Tech Shift"}] * 5) is True
    assert count_at_most_5([{"category": "Tech Shift"}] * 3) is True
    assert count_at_most_5([{"category": "Tech Shift"}] * 6) is False


# 6. Verdict validity
def test_verdict_valid():
    for v in ["WATCH", "INTEGRATE", "READ"]:
        assert verdict_valid(v) is True
    assert verdict_valid("IGNORE") is False
    assert verdict_valid("SKIP") is False
    assert verdict_valid("") is False


# 7. Required fields present
def test_required_fields_present():
    good = {
        "category": "Tech Shift",
        "title": "Clean Title",
        "description": "**Bold lead.** Description text.",
        "why_it_matters": "Real engineering value.",
        "who_cares": "Backend engineers.",
        "verdict": "INTEGRATE",
        "source_url": "https://github.com/example/repo",
    }
    assert required_fields_present(good) is True

    bad = good.copy()
    bad["title"] = ""  # empty field
    assert required_fields_present(bad) is False

    bad_missing = good.copy()
    del bad_missing["why_it_matters"]
    assert required_fields_present(bad_missing) is False


# 8. HTTPS source URL
def test_url_valid_https():
    assert url_valid_https("https://github.com/foo/bar") is True
    assert url_valid_https("http://github.com/foo/bar") is False
    assert url_valid_https("not-a-url") is False


# 9. Source URL matching candidate URLs (ignoring UTM parameters and trailing slashes)
def test_source_url_in_candidates():
    candidates = ["https://github.com/coollabsio/coolify/"]
    brief_good = {"source_url": "https://github.com/coollabsio/coolify?utm_source=hackernews"}
    brief_bad = {"source_url": "https://github.com/other/project"}
    assert source_url_in_candidates(brief_good, candidates) is True
    assert source_url_in_candidates(brief_bad, candidates) is False


# 10. Generic fallback text
def test_is_generic_fallback_text():
    bad1 = "A new open source development in the AI ecosystem."
    bad2 = "A notable new development in the cloud ecosystem."
    good = "Next.js introduces canary support for automated server components."
    assert is_generic_fallback_text(bad1) is True
    assert is_generic_fallback_text(bad2) is True
    assert is_generic_fallback_text(good) is False


# 11. Unsupported numeric tokens (versions, multipliers, percentages, suffixes, counts)
def test_unsupported_numeric_tokens():
    # Versions: v4, v1.2.3, 3.0
    brief_v = "Released Coolify v4 and Coolify 3.0 today."
    evidence_v = "Coolify v4 is released."
    assert "3.0" in unsupported_numeric_tokens(brief_v, evidence_v)
    assert "v4" not in unsupported_numeric_tokens(brief_v, evidence_v)

    # Multipliers: 10x
    assert "10x" in unsupported_numeric_tokens("Runs 10x faster.", "Runs faster.")
    assert len(unsupported_numeric_tokens("Runs 10x faster.", "Runs 10x faster.")) == 0

    # Percentages: 40%
    assert "40%" in unsupported_numeric_tokens("40% speedup.", "Faster speed.")
    assert len(unsupported_numeric_tokens("40% speedup.", "40% speedup.")) == 0

    # Suffixes: 250k
    assert "250k" in unsupported_numeric_tokens("Scanned 250k repos.", "Scanned many repos.")
    assert len(unsupported_numeric_tokens("Scanned 250k repos.", "Scanned 250k repos.")) == 0

    # Counts: 280+
    assert "280+" in unsupported_numeric_tokens("Supports 280+ tools.", "Supports many tools.")
    assert len(unsupported_numeric_tokens("Supports 280+ tools.", "Supports 280+ tools.")) == 0

    # Comma normalization: 1,000 matches 1000
    assert len(unsupported_numeric_tokens("Processed 1,000 files.", "Processed 1000 files.")) == 0

    # Evidence window: token at character 2000 is found when evidence is large
    long_evidence = "x" * 2000 + " version 5.0 is supported"
    assert len(unsupported_numeric_tokens("Supports v5.0 now.", long_evidence)) == 0


# 12. Full validate_briefs integration
def test_validate_briefs_integration():
    valid_brief = {
        "category": "Cool Tool",
        "title": "Diagrams",
        "description": "**Draw system architecture in Python code.** Supports AWS, GCP, and Kubernetes.",
        "why_it_matters": "Prototyping architecture without manual tools saves time.",
        "who_cares": "DevOps engineers and backend developers.",
        "verdict": "INTEGRATE",
        "source_url": "https://github.com/mingrammer/diagrams",
    }
    candidate_urls = ["https://github.com/mingrammer/diagrams"]
    assert validate_briefs([valid_brief], candidate_urls=candidate_urls) == []

    # Flag duplicate category, missing bold lead, invalid category, and bad URL
    invalid_brief = valid_brief.copy()
    invalid_brief["category"] = "BadCategory"
    invalid_brief["description"] = "No bold lead sentence here."
    invalid_brief["source_url"] = "http://insecure.url"
    violations = validate_briefs([valid_brief, invalid_brief], candidate_urls=candidate_urls)
    assert len(violations) >= 3


def test_history_fixture_checks():
    """Verify quality checks on published history entries."""
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        history = json.load(f)

    # 2026-09-04 was a degraded run (duplicate categories, missing bold leads)
    sep_04 = next((d for d in history if d.get("date") == "2026-09-04"), None)
    assert sep_04 is not None
    violations_04 = validate_briefs(sep_04.get("briefs", []))
    assert len(violations_04) > 0

    # 2026-10-11 was a healthy run
    oct_11 = next((d for d in history if d.get("date") == "2026-10-11"), None)
    assert oct_11 is not None
    violations_11 = validate_briefs(oct_11.get("briefs", []))
    assert len(violations_11) == 0


def test_number_in_source_title_is_not_flagged():
    url = "https://example.com/p"
    brief = {
        "category": "Tech Shift",
        "title": "Scan of 250k Files",
        "description": "**Researchers scanned 250k files.** More.",
        "why_it_matters": "Shows a common mistake.",
        "who_cares": "Web developers",
        "verdict": "READ",
        "source_url": url,
    }
    cand = {
        "title": "Scan of 250k Files",
        "description": "Security analysis.",
        "detailed_content": "Researchers scanned many repos.",
    }
    assert validate_briefs([brief], evidence_by_url={url: build_evidence(cand, 3000)}, candidate_urls={url}) == []


def test_number_absent_from_title_and_evidence_is_flagged():
    url = "https://example.com/p"
    brief = {
        "category": "Tech Shift",
        "title": "Scan of 250k Files",
        "description": "**Researchers scanned 350k files.** More.",
        "why_it_matters": "Shows a common mistake.",
        "who_cares": "Web developers",
        "verdict": "READ",
        "source_url": url,
    }
    cand = {
        "title": "Scan of 250k Files",
        "description": "Security analysis.",
        "detailed_content": "Researchers scanned many repos.",
    }
    assert len(validate_briefs([brief], evidence_by_url={url: build_evidence(cand, 3000)}, candidate_urls={url})) > 0

