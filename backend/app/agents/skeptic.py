import json
import logging
from typing import Dict, Any, List
from app.agents.state import AgentState
from app.agents.models import get_llm
from app.database import read_history

logger = logging.getLogger("DailyDiff.skeptic")

def extract_history_summary() -> str:
    """Read history.json and build a compact summary of recently published topics."""
    history = read_history()
    if not history:
        return "No past briefs have been published yet."
        
    summary_lines = []
    # Take up to the last 20 daily briefs groups to keep context window clean
    for day in history[-20:]:
        date = day.get("date", "Unknown Date")
        briefs = day.get("briefs", [])
        for b in briefs:
            summary_lines.append(f"- [{date}] {b.get('category', 'UPDATE')}: {b.get('title')} - {b.get('description')[:120]}...")
            
    return "\n".join(summary_lines)

def deduplicate_and_filter_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node. Checks raw signals against history for novelty,
    and applies a critic filter to reject minor updates/hype.
    """
    logger.info("Starting Skeptic / Deduplication node...")
    raw_signals = state.get("raw_signals", [])
    if not raw_signals:
        logger.warning("No raw signals found to evaluate.")
        return {"candidates": []}
        
    history_summary = extract_history_summary()
    
    # Format candidates for the LLM
    formatted_signals = []
    for idx, s in enumerate(raw_signals):
        formatted_signals.append(
            f"ID: {idx}\n"
            f"Source: {s['source']}\n"
            f"Title: {s['title']}\n"
            f"Description: {s['description']}\n"
            f"URL: {s['url']}\n"
            "---"
        )
    signals_text = "\n".join(formatted_signals)
    
    prompt = f"""You are the Skeptic Agent for DailyDiff, a technical intelligence platform.
Your job is to identify which of today's raw technology signals are NOVEL and SUBSTANTIAL.

Here is a list of topics we have already covered recently:
{history_summary}

Here are the new candidate signals discovered today:
{signals_text}

Analyze each candidate signal against the history and your technical knowledge.
1. DEDUPLICATION: Reject candidates that represent topics we have already covered, or are mere minor/incremental versions of them.
2. HYPE FILTER: Reject candidates that are purely marketing hype, temporary popularity spikes without technical substance, simple tutorials, or clickbait.
3. VALUE RATING: Identify candidates that represent meaningful shifts, core library releases, outstanding research, or high-momentum open-source projects.

Output a JSON array containing ONLY the IDs (integer numbers) of the signals that pass your filter. 
Format your response exactly like this:
[1, 4, 12]

Do not include any code block markdown like ```json or any other text. Return only the raw JSON array.
"""
    
    llm = get_llm(temperature=0.0)
    candidates = []
    
    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        
        # Clean up any potential markdown wrapping from LLM
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
                    if 0 <= idx < len(raw_signals):
                        candidates.append(raw_signals[idx])
                except (ValueError, TypeError):
                    continue
        logger.info(f"Skeptic filter complete: {len(candidates)} of {len(raw_signals)} signals passed.")
    except Exception as e:
        logger.error(f"Skeptic node error: {e}. Falling back to keeping top 10 raw signals.")
        # Fallback: keep first 10 signals to avoid blocking the run
        candidates = raw_signals[:10]
        
    return {"candidates": candidates}
