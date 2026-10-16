"""
Quality rules and validation checks for DailyDiff briefs.
Ensures publication briefs are well-formatted, factual, and actionable.
"""

import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qsl, urlunparse, urlencode

DESIGNATED_CATEGORIES = {"Tech Shift", "Cool Tool", "Career & Learning", "Ecosystem Update", "Watchlist"}
GENERIC_PATTERNS = ["a new open source development in the", "a notable new development in the"]

def build_evidence(candidate: Dict[str, Any], max_chars: int) -> str:
    """Everything a brief may quote: the source title, its description, and the first max_chars of its page text."""
    return f"{candidate.get('title', '')} {candidate.get('description', '')} {(candidate.get('detailed_content') or '')[:max_chars]}"


def has_bold_lead(desc: str) -> bool:
    d = (desc or "").strip()
    return d.startswith("**") and d.find("**", 2) > 2

def no_tldr_label(desc: str) -> bool:
    low = (desc or "").lower()
    return "tl;dr:" not in low and "tldr:" not in low

def categories_unique(briefs: List[Dict[str, Any]]) -> bool:
    cats = [b.get("category") for b in briefs if b.get("category")]
    return len(cats) == len(set(cats))

def count_at_most_5(briefs: List[Dict[str, Any]]) -> bool:
    return len(briefs) <= 5

def verdict_valid(v: str) -> bool:
    return str(v).upper() in {"WATCH", "INTEGRATE", "READ"}

def category_valid(b: Dict[str, Any]) -> bool:
    return b.get("category") in DESIGNATED_CATEGORIES

def required_fields_present(b: Dict[str, Any]) -> bool:
    for req in ["category", "title", "description", "why_it_matters", "who_cares", "verdict", "source_url"]:
        if not str(b.get(req) or "").strip():
            return False
    return True

def url_valid_https(url: str) -> bool:
    return str(url).strip().startswith("https://")

def normalize_url(url: str) -> str:
    if not url:
        return ""
    p = urlparse(url.strip().lower())
    q = [(k, v) for k, v in parse_qsl(p.query) if not k.startswith("utm_")]
    return urlunparse((p.scheme, p.netloc, p.path.rstrip("/"), p.params, urlencode(q), "")).rstrip("/")

def source_url_in_candidates(brief: Dict[str, Any], candidates: Any) -> bool:
    c_set = {normalize_url(u) for u in candidates if u}
    return normalize_url(brief.get("source_url", "")) in c_set

def is_generic_fallback_text(text: str) -> bool:
    return any(p in (text or "").lower() for p in GENERIC_PATTERNS)

def unsupported_numeric_tokens(brief_text: str, evidence_text: str) -> List[str]:
    """Finds numbers (versions, 10x, 40%, 250k, 280+) not present in the evidence."""
    if not brief_text or not evidence_text:
        return []
    clean_ev, clean_br = re.sub(r'(?<=\d),(?=\d)', '', evidence_text).lower(), re.sub(r'(?<=\d),(?=\d)', '', brief_text).lower()
    patterns = [r'\b(?:v)?\d+(?:\.\d+)+(?:-[a-z0-9.]+)?\b', r'\bv\d+\b', r'\b\d+(?:\.\d+)?x\b', r'\b\d+(?:\.\d+)?%', r'\b\d+(?:\.\d+)?[kmb]\b', r'\b\d+\+']
    tokens = set()
    for pat in patterns:
        tokens.update(re.findall(pat, clean_br))
    unsupported = []
    for tok in sorted(tokens):
        alt = tok.lstrip("v") if "." in tok else tok
        if tok not in clean_ev and alt not in clean_ev and f"version {tok[1:]}" not in clean_ev:
            unsupported.append(tok)
    return unsupported

def validate_briefs(briefs: List[Dict[str, Any]], evidence_by_url: Optional[Dict[str, str]] = None, candidate_urls: Optional[Any] = None) -> List[str]:
    violations = []
    if not briefs:
        return ["Empty briefs list: zero briefs provided."]
    if not count_at_most_5(briefs):
        violations.append(f"Count violation: {len(briefs)} exceeds maximum 5.")
    if not categories_unique(briefs):
        violations.append("Category uniqueness violation: duplicate categories assigned.")

    for b in briefs:
        t = b.get("title", "Untitled")
        if not required_fields_present(b):
            violations.append(f"Brief '{t}' missing required non-empty fields.")
        if not category_valid(b):
            violations.append(f"Brief '{t}' invalid category '{b.get('category')}'.")
        if not has_bold_lead(b.get("description", "")):
            violations.append(f"Brief '{t}' missing prepended bold lead-in.")
        if not no_tldr_label(b.get("description", "")):
            violations.append(f"Brief '{t}' contains forbidden TL;DR label.")
        if not verdict_valid(b.get("verdict", "")):
            violations.append(f"Brief '{t}' invalid verdict '{b.get('verdict')}'.")
        if not url_valid_https(b.get("source_url", "")):
            violations.append(f"Brief '{t}' source URL not HTTPS.")
        if candidate_urls is not None and not source_url_in_candidates(b, candidate_urls):
            violations.append(f"Brief '{t}' source_url '{b.get('source_url')}' is not in candidate URLs.")
        if is_generic_fallback_text(b.get("description", "")) or is_generic_fallback_text(b.get("why_it_matters", "")):
            violations.append(f"Brief '{t}' contains generic fallback text.")
        if evidence_by_url and b.get("source_url") in evidence_by_url:
            comb = f"{t} {b.get('description', '')} {b.get('why_it_matters', '')}"
            bad_nums = unsupported_numeric_tokens(comb, evidence_by_url[b.get("source_url")])
            if bad_nums:
                violations.append(f"Brief '{t}' has unsupported numbers: {bad_nums}")
    return violations
