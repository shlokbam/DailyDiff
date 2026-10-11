import json
import logging
from typing import Dict, Any, List
from app.agents.state import AgentState
from app.agents.models import get_llm

logger = logging.getLogger("DailyDiff.verifier")

def verifier_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node to verify technical assertions for all researched candidates
    in a single batched LLM call to prevent rate limiting and latency spikes.
    """
    logger.info("Starting Verifier Agent node (batched)...")
    researched = state.get("researched_candidates", [])
    if not researched:
        logger.warning("No researched candidates to verify.")
        return {"vetted_candidates": []}

    formatted_items = []
    for idx, c in enumerate(researched):
        formatted_items.append(
            f"ID: {idx}\n"
            f"Title: {c['title']}\n"
            f"Summary Claims: {c.get('description', '')}\n"
            f"Reference Documentation:\n{c.get('detailed_content', '')[:1200]}\n"
            "---"
        )
    candidates_text = "\n".join(formatted_items)

    prompt = f"""You are the technical Verifier Agent for DailyDiff.
Your task is to fact-check candidate developments against their reference documentation.

Candidates to verify:
{candidates_text}

For each candidate:
1. Are there any false assertions, contradictions, or significant exaggerations?
2. Is the candidate repository/paper real and functional based on the text (not just an empty placeholder repository)?

Output a JSON array containing ONLY the integer IDs of candidates that are VALID and supported.
Example format:
[0, 1, 3]

Do not include any code block markdown like ```json or any other text. Return only the raw JSON array.
"""

    llm = get_llm(temperature=0.0)
    vetted = []

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()

        # Clean markdown wrappers if present
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        passed_ids = json.loads(content)
        if isinstance(passed_ids, list):
            for pid in passed_ids:
                try:
                    idx = int(pid)
                    if 0 <= idx < len(researched):
                        vetted.append(researched[idx])
                except (ValueError, TypeError):
                    continue

        logger.info(f"Batched Verifier complete: {len(vetted)} of {len(researched)} candidates vetted successfully.")
    except Exception as e:
        logger.error(f"Batched Verifier LLM call failed: {e}. Falling back to substantive candidates.")
        # Fallback: keep candidates with substantial description
        vetted = [c for c in researched if len(c.get("description", "")) > 50]

    return {"vetted_candidates": vetted}

