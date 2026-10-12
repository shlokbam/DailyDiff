import re
from typing import List, Dict, Any, Optional

GENERIC_FALLBACK_PATTERNS = [
    "a new open source development in the",
    "a notable new development in the",
]

def has_bold_lead(description: str) -> bool:
    """Checks if the description begins with a markdown bold summary lead-in."""
    if not isinstance(description, str):
        return False
    desc = description.strip()
    if not desc.startswith("**"):
        return False
    closing_idx = desc.find("**", 2)
    return closing_idx > 2

def no_tldr_label(description: str) -> bool:
    """Checks that the description does not contain forbidden 'TL;DR:' or 'TLDR:' prefix labels."""
    if not isinstance(description, str):
        return True
    lower = description.lower()
    return "tl;dr:" not in lower and "tldr:" not in lower

def categories_unique(briefs: List[Dict[str, Any]]) -> bool:
    """Checks that each assigned briefing category appears at most once across the daily brief."""
    if not isinstance(briefs, list):
        return False
    categories = [b.get("category") for b in briefs if b.get("category")]
    return len(categories) == len(set(categories))

def count_at_most_5(briefs: List[Dict[str, Any]]) -> bool:
    """Checks that at most 5 briefs are included in the daily publication."""
    if not isinstance(briefs, list):
        return False
    return len(briefs) <= 5

def verdict_valid(verdict: str) -> bool:
    """Checks that the verdict is one of WATCH, INTEGRATE, READ."""
    if not isinstance(verdict, str):
        return False
    return verdict.upper() in {"WATCH", "INTEGRATE", "READ"}

def required_fields_present(brief: Dict[str, Any]) -> bool:
    """Checks that all essential fields are non-empty strings."""
    if not isinstance(brief, dict):
        return False
    required = ["category", "title", "description", "why_it_matters", "who_cares", "verdict", "source_url"]
    for req in required:
        val = brief.get(req)
        if val is None or not str(val).strip():
            return False
    return True

def url_valid_https(url: str) -> bool:
    """Checks that the reference URL is a valid HTTPS web link."""
    if not isinstance(url, str):
        return False
    return url.strip().startswith("https://")

def is_generic_fallback_text(text: str) -> bool:
    """
    Checks if text contains degraded generic boilerplate.
    Matches both 'A new open source development in the' and 'A notable new development in the'.
    """
    if not isinstance(text, str):
        return False
    lower = text.lower()
    return any(pattern in lower for pattern in GENERIC_FALLBACK_PATTERNS)

def unsupported_numeric_tokens(brief_text: str, evidence_text: str) -> List[str]:
    """
    Returns numbers and version strings (e.g. 'v4.2', '3.0', '250k') that appear
    in the brief text but never appear in the reference evidence.
    """
    if not brief_text or not evidence_text:
        return []

    # Extract version strings, numbers with decimals, or numbers with k/m suffixes
    pattern = r'\b(?:v)?\d+(?:\.\d+)+(?:-[a-zA-Z0-9.]+)?\b'
    brief_tokens = set(re.findall(pattern, brief_text, re.IGNORECASE))

    evidence_lower = evidence_text.lower()
    unsupported = []
    for token in brief_tokens:
        clean_tok = token.lower().lstrip("v")
        if clean_tok not in evidence_lower and token.lower() not in evidence_lower:
            unsupported.append(token)

    return sorted(unsupported)

def validate_briefs(
    briefs: List[Dict[str, Any]],
    evidence_by_url: Optional[Dict[str, str]] = None
) -> List[str]:
    """
    Validates candidate briefs against all quality rules.
    Returns an empty list if healthy, or a list of violation description strings.
    """
    violations = []

    if not briefs:
        violations.append("Empty briefs list: zero briefs provided for validation.")
        return violations

    if not count_at_most_5(briefs):
        violations.append(f"Count violation: {len(briefs)} briefs exceeds maximum allowance of 5.")

    if not categories_unique(briefs):
        seen_cats = {}
        for b in briefs:
            cat = b.get("category")
            seen_cats[cat] = seen_cats.get(cat, 0) + 1
        dup_cats = [cat for cat, cnt in seen_cats.items() if cnt > 1]
        violations.append(f"Category uniqueness violation: duplicate categories assigned: {dup_cats}.")

    for idx, b in enumerate(briefs):
        title = b.get("title", f"brief #{idx}")

        if not required_fields_present(b):
            violations.append(f"Brief '{title}' missing required non-empty fields.")

        desc = b.get("description", "")
        if not has_bold_lead(desc):
            violations.append(f"Brief '{title}' missing prepended bold lead-in summary in description.")

        if not no_tldr_label(desc):
            violations.append(f"Brief '{title}' contains forbidden TL;DR / TLDR prefix label in description.")

        verdict = b.get("verdict", "")
        if not verdict_valid(verdict):
            violations.append(f"Brief '{title}' has invalid verdict '{verdict}'. Must be WATCH, INTEGRATE, or READ.")

        url = b.get("source_url", "")
        if not url_valid_https(url):
            violations.append(f"Brief '{title}' has invalid source URL '{url}'. Must start with https://.")

        why = b.get("why_it_matters", "")
        if is_generic_fallback_text(why) or is_generic_fallback_text(desc):
            violations.append(f"Brief '{title}' contains degraded generic fallback text.")

        if evidence_by_url and url in evidence_by_url:
            evidence = evidence_by_url.get(url, "")
            combined_text = f"{title} {desc} {why}"
            unsupported = unsupported_numeric_tokens(combined_text, evidence)
            if unsupported:
                violations.append(f"Brief '{title}' introduces unsupported version/numeric tokens not in evidence: {unsupported}")

    return violations
