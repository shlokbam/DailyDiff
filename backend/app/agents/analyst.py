import logging
import json
from typing import Dict, Any, List
from app.agents.state import AgentState
from app.agents.models import get_llm

logger = logging.getLogger("DailyDiff.analyst")

def analyst_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node to analyze all vetted candidates in a single batched LLM call
    to prevent rate limits and speed up execution from minutes to seconds.
    """
    logger.info("Starting Analyst Agent node (batched)...")
    vetted = state.get("vetted_candidates", [])
    if not vetted:
        logger.warning("No vetted candidates to analyze.")
        return {"vetted_candidates": []}

    formatted_items = []
    for idx, c in enumerate(vetted):
        formatted_items.append(
            f"ID: {idx}\n"
            f"Title: {c['title']}\n"
            f"Source: {c['source']}\n"
            f"URL: {c['url']}\n"
            f"Content:\n{c.get('detailed_content', c.get('description', ''))[:1000]}\n"
            "---"
        )
    candidates_text = "\n".join(formatted_items)

    prompt = f"""You are the Analyst Agent for DailyDiff.
Analyze the following technology developments and extract structured practical insights for tech students and early-career software developers.

Candidates to evaluate:
{candidates_text}

For each candidate, output an analysis object with:
- "id": integer candidate ID matching the input
- "why_it_matters": 1-2 clear, punchy sentences explaining practical value (helps learn, build faster, save time, understand a concept).
- "who_cares": Specific developer groups or learner roles (e.g., "CS students building portfolios, React beginners, junior frontend developers, python learners").
- "verdict": Exactly one of: "WATCH", "INTEGRATE", "READ", "IGNORE".
- "confidence": Integer 0 to 100 representing confidence in this development's momentum and quality.

Format your response as a valid JSON array of objects:
[
  {{
    "id": 0,
    "why_it_matters": "...",
    "who_cares": "...",
    "verdict": "INTEGRATE",
    "confidence": 90
  }}
]

Do not include any code block markdown like ```json or any other text. Return only the raw JSON array.
"""

    llm = get_llm(temperature=0.2)
    analyzed = []

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

        analysis_list = json.loads(content)
        analysis_map = {}
        if isinstance(analysis_list, list):
            for item in analysis_list:
                if isinstance(item, dict) and "id" in item:
                    try:
                        analysis_map[int(item["id"])] = item
                    except (ValueError, TypeError):
                        pass

        for idx, c in enumerate(vetted):
            item_analysis = analysis_map.get(idx, {})
            c_copy = c.copy()
            c_copy["why_it_matters"] = item_analysis.get("why_it_matters") or f"A notable new development in the {c.get('source', 'tech')} ecosystem."
            c_copy["who_cares"] = item_analysis.get("who_cares") or "Tech students, early-career software engineers"
            c_copy["verdict"] = item_analysis.get("verdict") or "WATCH"
            c_copy["confidence"] = int(item_analysis.get("confidence", 80))
            analyzed.append(c_copy)

        logger.info(f"Batched Analyst node complete: processed {len(analyzed)} candidates.")
    except Exception as e:
        logger.error(f"Batched Analyst node error: {e}. Applying fallback analysis.")
        for c in vetted:
            fallback = c.copy()
            fallback["why_it_matters"] = f"A notable new development in the {c.get('source', 'tech')} ecosystem."
            fallback["who_cares"] = "Tech students, software engineers"
            fallback["verdict"] = "WATCH"
            fallback["confidence"] = 75
            analyzed.append(fallback)

    return {"vetted_candidates": analyzed}
