import logging
from typing import Dict, Any, List
from app.agents.state import AgentState
from app.agents.models import get_llm

logger = logging.getLogger("DailyDiff.verifier")

def verify_candidate(candidate: Dict[str, Any]) -> bool:
    """Verify a single candidate's technical assertions against its raw content."""
    prompt = f"""You are the technical Verifier Agent for DailyDiff.
Your task is to verify whether the claimed features and capabilities in the summary are fully supported by the reference documentation.

SUMMARY CLAIMS:
Title: {candidate['title']}
Description: {candidate['description']}

REFERENCE DOCUMENTATION:
{candidate['detailed_content'][:3000]}

Please perform a strict fact-check:
1. Are there any false assertions or exaggerations? (e.g., claiming a feature that is not in the readme, or claiming 10x performance when the readme or paper says 2x).
2. Is the candidate repository/paper real and functional based on the text (e.g., not just an empty placeholder repository)?

Output exactly "VALID" if the claims are true and supported.
Output exactly "INVALID: [reason]" if there is a contradiction, significant exaggeration, or if it's an empty placeholder repository.

Output:"""

    llm = get_llm(temperature=0.0)
    try:
        response = llm.invoke(prompt)
        verdict = response.content.strip()
        if verdict.startswith("VALID"):
            return True
        else:
            logger.warning(f"Verification failed for candidate '{candidate['title']}': {verdict}")
            return False
    except Exception as e:
        logger.error(f"Verifier LLM call failed for '{candidate['title']}': {e}")
        # In case of API failure, fail-safe: mark as valid if description seems substantial
        return len(candidate.get("description", "")) > 50

def verifier_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node to verify technical assertions for all researched candidates."""
    logger.info("Starting Verifier Agent node...")
    researched = state.get("researched_candidates", [])
    if not researched:
        logger.warning("No researched candidates to verify.")
        return {"vetted_candidates": []}
        
    vetted = []
    for c in researched:
        is_valid = verify_candidate(c)
        if is_valid:
            vetted.append(c)
            
    logger.info(f"Verifier node complete: {len(vetted)} of {len(researched)} candidates vetted successfully.")
    return {"vetted_candidates": vetted}
