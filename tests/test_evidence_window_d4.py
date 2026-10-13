import pytest
from app.checks import validate_briefs
from app.agents.researcher import MAX_EVIDENCE_CHARS

def test_version_at_char_2000_passes_validation():
    filler = "word " * 399 # ~2000 characters
    assert len(filler) >= 1990
    readme = filler + " Release version v2.5.0 includes major performance enhancements."
    assert len(readme) <= MAX_EVIDENCE_CHARS
    assert readme.find("v2.5.0") >= 1990

    url = "https://github.com/framework/v2"
    brief = {
        "title": "Framework Update",
        "category": "Tech Shift",
        "description": "**Framework v2.5.0 delivers major performance enhancements.** What happened: Performance enhancements were released in v2.5.0.",
        "why_it_matters": "Improves developer productivity.",
        "who_cares": "Engineers.",
        "verdict": "INTEGRATE",
        "source_url": url
    }

    evidence_by_url = {url: readme[:MAX_EVIDENCE_CHARS]}
    candidate_urls = {url}

    violations = validate_briefs([brief], evidence_by_url=evidence_by_url, candidate_urls=candidate_urls)
    assert len(violations) == 0, f"Expected 0 violations, got: {violations}"

    # Verify that with the old 1200 character window, it would have failed
    old_evidence_by_url = {url: readme[:1200]}
    old_violations = validate_briefs([brief], evidence_by_url=old_evidence_by_url, candidate_urls=candidate_urls)
    assert len(old_violations) > 0
    assert any("v2.5.0" in v for v in old_violations)
