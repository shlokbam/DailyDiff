import logging
import re
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urlparse, parse_qsl, urlunparse, urlencode
from app.run_health import health

logger = logging.getLogger("DailyDiff.checks")

DESIGNATED_CATEGORIES: Set[str] = {
    "Tech Shift",
    "Cool Tool",
    "Career & Learning",
    "Ecosystem Update",
    "Watchlist",
}

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

def category_valid(brief: Dict[str, Any]) -> bool:
    """Checks that the category is one of the five designated categories."""
    if not isinstance(brief, dict):
        return False
    cat = brief.get("category")
    return isinstance(cat, str) and cat in DESIGNATED_CATEGORIES

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

def normalize_url(url: str) -> str:
    """Normalizes URL: lowercases, strips trailing slashes, and removes utm_* parameters."""
    if not isinstance(url, str) or not url.strip():
        return ""
    u = url.strip().lower()
    parsed = urlparse(u)
    filtered_q = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
    new_query = urlencode(filtered_q)
    path = parsed.path.rstrip("/")
    normalized = urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, new_query, ""))
    return normalized.rstrip("/")

def source_url_in_candidates(brief: Dict[str, Any], candidate_urls: Any) -> bool:
    """Checks if the brief's source_url matches one of the candidate URLs (after normalization)."""
    if not isinstance(brief, dict):
        return False
    raw_url = brief.get("source_url", "")
    if not raw_url:
        return False
    norm_url = normalize_url(raw_url)
    if not norm_url:
        return False
    candidates_set = {normalize_url(u) for u in candidate_urls if u}
    return norm_url in candidates_set

def is_generic_fallback_text(text: str) -> bool:
    """
    Checks if text contains degraded generic boilerplate.
    Matches both 'A new open source development in the' and 'A notable new development in the'.
    """
    if not isinstance(text, str):
        return False
    lower = text.lower()
    return any(pattern in lower for pattern in GENERIC_FALLBACK_PATTERNS)

def _normalize_text_for_numbers(text: str) -> str:
    """Normalizes case and thousands separators (e.g. 10,000 -> 10000)."""
    return re.sub(r'(?<=\d),(?=\d)', '', text).lower()

def unsupported_numeric_tokens(brief_text: str, evidence_text: str) -> List[str]:
    """
    Returns numbers and version strings (e.g. 'v4', 'v4.2', '3.0', '10x', '40%', '250k', '280+')
    that appear in the brief text but never appear in the reference evidence.
    Normalizes case and thousands separators before comparison.
    """
    if not brief_text or not evidence_text:
        return []

    norm_evidence = _normalize_text_for_numbers(evidence_text)
    norm_brief = _normalize_text_for_numbers(brief_text)

    # 1. Dotted versions: v1.2.3, 3.0, 1.45.1
    dotted = re.findall(r'\b(?:v)?\d+(?:\.\d+)+(?:-[a-zA-Z0-9.]+)?\b', norm_brief)
    # 2. Bare versions: v4, v10 (v followed by digits)
    bare = re.findall(r'\bv\d+\b', norm_brief)
    # 3. Multipliers: 10x, 2.5x (digits optionally dot digits followed by x)
    multipliers = re.findall(r'\b\d+(?:\.\d+)?x\b', norm_brief)
    # 4. Percentages: 40%, 99.9%
    percentages = re.findall(r'\b\d+(?:\.\d+)?%', norm_brief)
    # 5. Numbers with k/m/b suffixes: 250k, 10m, 1b
    suffixes = re.findall(r'\b\d+(?:\.\d+)?[kmb]\b', norm_brief)
    # 6. Counts: 280+
    counts = re.findall(r'\b\d+\+', norm_brief)

    all_tokens = set(dotted + bare + multipliers + percentages + suffixes + counts)

    unsupported = []
    for token in all_tokens:
        clean_tok = token.lstrip("v") if ("." in token) else token
        # Check direct presence or alternative version wording
        is_supported = (
            clean_tok in norm_evidence
            or token in norm_evidence
            or (token.startswith("v") and not "." in token and f"version {token[1:]}" in norm_evidence)
        )
        if not is_supported:
            unsupported.append(token)

    return sorted(unsupported)

def validate_briefs(
    briefs: List[Dict[str, Any]],
    evidence_by_url: Optional[Dict[str, str]] = None,
    candidate_urls: Optional[Any] = None
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

    if candidate_urls is None:
        warning_msg = "validate_briefs: candidate_urls not provided for candidate URL verification."
        logger.warning(warning_msg)
        health.add_warning(warning_msg)

    for idx, b in enumerate(briefs):
        title = b.get("title", f"brief #{idx}")

        if not required_fields_present(b):
            violations.append(f"Brief '{title}' missing required non-empty fields.")

        if not category_valid(b):
            violations.append(f"Brief '{title}' has invalid category '{b.get('category')}'. Must be one of designated categories.")

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

        if candidate_urls is not None:
            if not source_url_in_candidates(b, candidate_urls):
                violations.append(f"Brief '{title}' source_url '{url}' is not in candidate URLs.")

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

