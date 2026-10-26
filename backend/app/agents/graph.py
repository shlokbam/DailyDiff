import logging
from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.scout import scout_ecosystem_node
from app.agents.skeptic import deduplicate_and_filter_node
from app.agents.researcher import research_candidates_node
from app.agents.verifier import verifier_node
from app.agents.analyst import analyst_node
from app.agents.editor import editor_node
from app.run_state import STAGES

logger = logging.getLogger("DailyDiff.graph")

def create_agent_graph(start_at: str = "scout"):
    """Build and compile the LangGraph workflow, starting at `start_at` (used to resume a failed run)."""
    if start_at not in STAGES:
        raise ValueError(f"Unknown start stage '{start_at}'. Expected one of {STAGES}.")

    # Looked up at call time so tests can patch the node functions
    node_fns = {
        "scout": scout_ecosystem_node,
        "skeptic": deduplicate_and_filter_node,
        "research": research_candidates_node,
        "verify": verifier_node,
        "analyze": analyst_node,
        "editor": editor_node,
    }

    # Only add the stages from start_at onward: langgraph refuses unreachable nodes
    stages = STAGES[STAGES.index(start_at):]
    workflow = StateGraph(AgentState)
    for stage in stages:
        workflow.add_node(stage, node_fns[stage])

    # Establish graph execution flow
    workflow.set_entry_point(stages[0])
    for current, nxt in zip(stages, stages[1:]):
        workflow.add_edge(current, nxt)
    workflow.add_edge(stages[-1], END)

    # Compile the graph
    app = workflow.compile()
    return app
