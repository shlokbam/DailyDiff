import logging
import json
from typing import Dict, Any, List
from app.agents.state import AgentState
from app.agents.models import get_llm

logger = logging.getLogger("DailyDiff.analyst")

def analyze_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a vetted candidate to determine practical value, audience, verdict, and confidence."""
    prompt = f"""You are the Analyst Agent for DailyDiff.
Analyze the following technology development and extract structured technical insights.

TITLE: {candidate['title']}
SOURCE: {candidate['source']}
URL: {candidate['url']}
DOCUMENTATION CONTENT:
{candidate['detailed_content'][:2000]}

Perform an evaluation and output a JSON object containing these keys:
- "why_it_matters": Write 1-2 clear, punchy sentences explaining why this matters. Skip generic summaries; focus on the practical shift or architectural impact.
- "who_cares": Identify the specific developer/engineering groups who should care (e.g., "AI engineers, agent developers, platform teams").
- "verdict": Actionable recommendation. Must be exactly one of: "WATCH" (early signal), "INTEGRATE" (mature and highly useful), "READ" (research paper of interest), "IGNORE" (low priority).
- "confidence": An integer score from 0 to 100 representing your confidence in this development's momentum and technical claims.

Format your response exactly like this (valid JSON only):
{{
  "why_it_matters": "...",
  "who_cares": "...",
  "verdict": "...",
  "confidence": 85
}}

Do not include any code block markdown like ```json or any other text. Return only the raw JSON string.
"""

    llm = get_llm(temperature=0.2)
    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        
        # Clean markdown wrappers if any
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()
            
        analysis = json.loads(content)
        
        analyzed = candidate.copy()
        analyzed["why_it_matters"] = analysis.get("why_it_matters", "")
        analyzed["who_cares"] = analysis.get("who_cares", "")
        analyzed["verdict"] = analysis.get("verdict", "WATCH")
        analyzed["confidence"] = int(analysis.get("confidence", 80))
        return analyzed
    except Exception as e:
        logger.error(f"Analyst node error for '{candidate['title']}': {e}")
        # Return fallback analysis
        fallback = candidate.copy()
        fallback["why_it_matters"] = f"A new open source development in the {candidate['source']} ecosystem."
        fallback["who_cares"] = "Developers, AI researchers"
        fallback["verdict"] = "WATCH"
        fallback["confidence"] = 75
        return fallback

def analyst_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node to analyze all vetted candidates."""
    logger.info("Starting Analyst Agent node...")
    vetted = state.get("vetted_candidates", [])
    if not vetted:
        logger.warning("No vetted candidates to analyze.")
        return {"vetted_candidates": []}
        
    analyzed = []
    import time
    for c in vetted:
        analyzed.append(analyze_candidate(c))
        time.sleep(1.0)  # Throttling LLM requests to safeguard API quotas
        
    logger.info(f"Analyst node complete: processed {len(analyzed)} candidates.")
    return {"vetted_candidates": analyzed}
