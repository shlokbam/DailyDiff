import logging
import json
from typing import Dict, Any, List
from app.agents.state import AgentState
from app.agents.models import get_llm

logger = logging.getLogger("DailyDiff.editor")

def editor_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node. Curates the final selection of up to 5 briefs,
    assigning each to a specific category and refining the text copy.
    """
    logger.info("Starting Editor Agent node...")
    vetted = state.get("vetted_candidates", [])
    if not vetted:
        logger.warning("No vetted candidates available for the Editor.")
        return {"final_briefs": []}
        
    # Serialize candidates to text for the Editor prompt
    candidates_data = []
    for idx, c in enumerate(vetted):
        candidates_data.append({
            "id": idx,
            "title": c["title"],
            "source": c["source"],
            "url": c["url"],
            "description": c["description"],
            "why_it_matters": c.get("why_it_matters", ""),
            "who_cares": c.get("who_cares", ""),
            "verdict": c.get("verdict", "WATCH"),
            "confidence": c.get("confidence", 80),
        })
        
    candidates_json = json.dumps(candidates_data, indent=2)
    
    prompt = f"""You are the Editor-in-Chief for DailyDiff.
Your task is to select up to 5 of the absolute strongest candidates from today's technology list, refine their text copy for publication, and assign each to one of our designated briefing categories.

DESIGNATED CATEGORIES (Use each category at most once):
- "Tech Shift": General tech industry news, shifts, hiring trends, or major developer announcements.
- "Cool Tool": Interesting new open-source projects, tools, starter templates, or SaaS apps that are practical to use or learn from.
- "Career & Learning": Career advice, job search tips, learning roadmaps, tutorial guides, or system design principles explained simply.
- "Ecosystem Update": Major framework updates, tool releases, or standard updates that affect how developers build software (e.g. GitHub Releases).
- "Watchlist": Early-stage concepts, cool tech trends, or rising libraries to keep on your radar.

RULES:
1. Select only the highest quality developments. If there are fewer than 5 high-quality candidates, select fewer (e.g. 2 or 3).
2. Clean up the titles, descriptions, "why_it_matters", and "who_cares" to be short, punchy, and highly readable.
3. Every item must have three fields answering: What happened?, Why it matters?, and Who cares?.
4. WRITING STYLE RULES (Extremely Important):
   - Tone: Write in an engaging, conversational, developer-friendly tech-blogger tone, NOT a dry academic review style.
   - ELI5 Rule (Explain Like I'm 5): Simplify all complex concepts. Do not use advanced mathematical/ML terms without explaining them in a simple, one-sentence analogy.
   - Focus on Practical Application, Not Theory: Frame the description and "Why it matters" around *what developers can build or learn* using this, rather than the theoretical backend mechanisms.
   - Prepend Summary: You MUST prepend a 1-sentence bold summary at the very beginning of the "description" field. Do NOT include the prefix label "TL;DR:". Example format: "**You can now deploy React apps directly to decentralized hosts in one click.** \n\nWhat happened..."

Candidates list:
{candidates_json}

Output a JSON array containing the selected, formatted briefs. Every item in the array must match this schema:
{{
  "category": "Tech Shift / Cool Tool / Career & Learning / Ecosystem Update / Watchlist",
  "title": "...",
  "description": "What happened text...",
  "why_it_matters": "Why it matters text...",
  "who_cares": "Who should care text...",
  "verdict": "WATCH / INTEGRATE / READ",
  "confidence": 85,
  "source_url": "..."
}}

Format your response exactly like this (valid JSON only):
[
  {{
    "category": "Tech Shift",
    "title": "...",
    ...
  }}
]

Do not include any code block markdown like ```json or any other text. Return only the raw JSON array.
"""

    llm = get_llm(temperature=0.3)
    final_briefs = []
    
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
            
        final_briefs = json.loads(content)
        logger.info(f"Editor curated {len(final_briefs)} final briefs successfully.")
    except Exception as e:
        logger.error(f"Editor node curation failed: {e}")
        # Fallback: convert the first 3 vetted candidates directly
        for c in vetted[:3]:
            final_briefs.append({
                "category": "Tech Shift" if c["source"] == "GitHub" else "Career & Learning",
                "title": c["title"],
                "description": c["description"],
                "why_it_matters": c.get("why_it_matters", "A notable new release worth examining."),
                "who_cares": c.get("who_cares", "Developers, software engineers"),
                "verdict": c.get("verdict", "WATCH"),
                "confidence": c.get("confidence", 80),
                "source_url": c["url"],
            })
            
    return {"final_briefs": final_briefs}
