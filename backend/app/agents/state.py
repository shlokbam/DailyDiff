from typing import List, Dict, Any, TypedDict, Annotated
import operator

class AgentState(TypedDict):
    # Raw signals collected by the Scout Agent
    raw_signals: List[Dict[str, Any]]
    
    # Candidates that are deemed novel and worth investigating
    candidates: List[Dict[str, Any]]
    
    # Detailed text and metadata fetched by the Researcher
    researched_candidates: List[Dict[str, Any]]
    
    # Candidates that passed structural verification and claims checking
    vetted_candidates: List[Dict[str, Any]]
    
    # Criticisms, hype scores, and revision advice from the Skeptic
    criticisms: List[Dict[str, Any]]
    
    # The final briefs (up to 5 items) synthesized by the Editor
    final_briefs: List[Dict[str, Any]]
    
    # Execution error logs (if any)
    errors: List[str]
