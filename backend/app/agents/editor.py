import logging
import json
from typing import Dict, Any, List
from app.agents.state import AgentState
from app.agents.models import get_llm, invoke_llm
from app.checks import validate_briefs
from app.run_health import health

logger = logging.getLogger("DailyDiff.editor")

DESIGNATED_CATEGORIES = [
    "Tech Shift",
    "Cool Tool",
    "Career & Learning",
    "Ecosystem Update",
    "Watchlist"
]

def _enforce_code_limits(briefs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Enforces at most 5 briefs and strict category uniqueness in Python code."""
    seen_cats = set()
    curated = []
    for b in briefs:
        cat = b.get("category")
        if cat and cat not in seen_cats:
            seen_cats.add(cat)
            curated.append(b)
        if len(curated) >= 5:
            break
    return curated

def _build_editor_prompt(candidates_json: str, feedback: str = "") -> str:
    feedback_section = ""
    if feedback:
        feedback_section = f"\nPREVIOUS ATTEMPT PRODUCED THESE VALIDATION VIOLATIONS:\n{feedback}\nYou must correct these violations in your output.\n"

    return f"""You are the Editor-in-Chief for DailyDiff.
Your task is to select up to 5 of the absolute strongest candidates from today's technology list, refine their text copy for publication, and assign each to one of our designated briefing categories.

DESIGNATED CATEGORIES (Use each category at most once):
- "Tech Shift": General tech industry news, shifts, hiring trends, or major developer announcements.
- "Cool Tool": Interesting new open-source projects, tools, starter templates, or SaaS apps that are practical to use or learn from.
- "Career & Learning": Career advice, job search tips, learning roadmaps, tutorial guides, or system design principles explained simply.
- "Ecosystem Update": Major framework updates, tool releases, or standard updates that affect how developers build software (e.g. GitHub Releases).
- "Watchlist": Early-stage concepts, cool tech trends, or rising libraries to keep on your radar.

STRICT GROUNDING & EDITORIAL RULES:
1. Grounding: Use ONLY facts explicitly present in the DESCRIPTION or EVIDENCE.
2. Hallucination Defense: Do NOT invent, extrapolate, or introduce numbers, version names (e.g. do not say "v4" if evidence says "v3"), benchmarks, or claims that are not in the source text.
3. Every item must have three fields answering: What happened?, Why it matters?, and Who cares?.
4. WRITING STYLE RULES:
   - Tone: Write in an engaging, conversational, developer-friendly tech-blogger tone, NOT a dry academic review style.
   - ELI5 Rule (Explain Like I'm 5): Simplify all complex concepts with intuitive, developer-friendly analogies.
   - Prepend Summary: You MUST prepend a 1-sentence bold summary at the very beginning of the "description" field. Example format: "**You can now deploy React apps directly to decentralized hosts in one click.** \n\nWhat happened..."
   - NO "TL;DR:" prefix: Do NOT include the prefix label "TL;DR:" or "TLDR:".
   - Unique Categories: Assign each chosen item a DIFFERENT category from the designated list. At most 5 items total.

Candidates list:
{candidates_json}
{feedback_section}
Output a JSON array containing the selected, formatted briefs matching this schema:
[
  {{
    "category": "Tech Shift",
    "title": "...",
    "description": "**Bold lead sentence.** Rest of description...",
    "why_it_matters": "Why it matters text...",
    "who_cares": "Who cares text...",
    "verdict": "WATCH / INTEGRATE / READ",
    "source_url": "https://..."
  }}
]

Do not include any code block markdown like ```json or any other text. Return only the raw JSON array.
"""

def editor_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node. Curates the final selection of up to 5 briefs,
    assigning unique categories and strictly enforcing grounding evidence.
    Fails closed (returns zero briefs) if output violates validation rules after retry.
    """
    logger.info("Starting Editor Agent node...")
    vetted = state.get("vetted_candidates", [])
    if not vetted:
        logger.warning("No vetted candidates available for the Editor.")
        health.set_count("final", 0)
        return {"final_briefs": []}

    candidates_data = []
    evidence_by_url = {}
    for idx, c in enumerate(vetted):
        content_src = c.get("content_source", "")
        evidence = ""
        if content_src in ["readme", "web_page"]:
            evidence = (c.get("detailed_content") or "")[:1200]

        url = c.get("url") or ""
        evidence_by_url[url] = f"{c.get('description', '')} {evidence}"

        candidates_data.append({
            "id": idx,
            "title": c.get("title", ""),
            "source": c.get("source", ""),
            "url": url,
            "description": c.get("description", ""),
            "evidence": evidence,
            "why_it_matters": c.get("why_it_matters", ""),
            "who_cares": c.get("who_cares", ""),
            "verdict": c.get("verdict", "WATCH"),
        })

    candidates_json = json.dumps(candidates_data, indent=2)
    prompt = _build_editor_prompt(candidates_json)

    llm = get_llm(temperature=0.2)
    final_briefs = []

    try:
        response = invoke_llm("editor", llm, prompt)
        content = response.content.strip()

        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        raw_briefs = json.loads(content)
        if isinstance(raw_briefs, list):
            # Enforce at most 5 and unique categories in Python
            final_briefs = _enforce_code_limits(raw_briefs)

        # Validate with pure checks
        violations = validate_briefs(final_briefs, evidence_by_url)
        if violations:
            logger.warning(f"Editor briefs had {len(violations)} violations. Retrying once with error feedback...")
            feedback = "\n".join(f"- {v}" for v in violations)
            retry_prompt = _build_editor_prompt(candidates_json, feedback=feedback)

            retry_resp = invoke_llm("editor", llm, retry_prompt)
            retry_content = retry_resp.content.strip()
            if retry_content.startswith("```"):
                lines = retry_content.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                retry_content = "\n".join(lines).strip()

            retry_briefs = json.loads(retry_content)
            if isinstance(retry_briefs, list):
                final_briefs = _enforce_code_limits(retry_briefs)

            retry_violations = validate_briefs(final_briefs, evidence_by_url)
            if retry_violations:
                logger.error(f"Editor briefs still have violations after retry: {retry_violations}. Dropping all briefs.")
                health.mark_fallback("editor", f"Violations after retry: {'; '.join(retry_violations[:3])}")
                final_briefs = []

        logger.info(f"Editor curated {len(final_briefs)} final briefs successfully.")
    except Exception as e:
        logger.error(f"Editor node curation failed: {e}. Failing closed.")
        health.mark_fallback("editor", str(e))
        final_briefs = []

    health.set_count("final", len(final_briefs))
    return {"final_briefs": final_briefs}
