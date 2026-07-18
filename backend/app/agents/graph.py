import logging
from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.scout import scout_ecosystem_node
from app.agents.skeptic import deduplicate_and_filter_node
from app.agents.researcher import research_candidates_node
from app.agents.verifier import verifier_node
from app.agents.analyst import analyst_node
from app.agents.editor import editor_node

logger = logging.getLogger("DailyDiff.graph")

def create_agent_graph():
    """Build and compile the LangGraph workflow for DailyDiff."""
    workflow = StateGraph(AgentState)
    
    # Add nodes to graph
    workflow.add_node("scout", scout_ecosystem_node)
    workflow.add_node("skeptic", deduplicate_and_filter_node)
    workflow.add_node("research", research_candidates_node)
    workflow.add_node("verify", verifier_node)
    workflow.add_node("analyze", analyst_node)
    workflow.add_node("editor", editor_node)
    
    # Establish graph execution flow
    workflow.set_entry_point("scout")
    workflow.add_edge("scout", "skeptic")
    workflow.add_edge("skeptic", "research")
    workflow.add_edge("research", "verify")
    workflow.add_edge("verify", "analyze")
    workflow.add_edge("analyze", "editor")
    workflow.add_edge("editor", END)
    
    # Compile the graph
    app = workflow.compile()
    return app
