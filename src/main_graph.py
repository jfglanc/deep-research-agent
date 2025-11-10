"""Main graph for Deep Research Agent system.

Flow: Advisor → Supervisor (Deep Agent) → Report Writer (Deep Agent) → END
"""

from typing_extensions import Literal
from langgraph.graph import StateGraph, START, END

# State
from src.state import FullResearchState

# Agents
from src.advisor.advisor_agent import advisor_agent  # UNCHANGED
from src.research_deep_agent import deep_research_supervisor  # NEW (Deep Agent)
from src.report_writer.report_writer import write_final_report  # MODIFIED (Deep Agent)


# ===== ROUTING LOGIC =====

def route_after_advisor(state: FullResearchState) -> Literal["supervisor", "__end__"]:
    """Route to supervisor if approved, otherwise end."""
    if state.get("user_approved"):
        return "supervisor"
    return END


# ===== GRAPH CONSTRUCTION =====

full_builder = StateGraph(FullResearchState)

# Add nodes
full_builder.add_node("advisor", advisor_agent)  # Unchanged
full_builder.add_node("supervisor", deep_research_supervisor)  # Deep Agent
full_builder.add_node("write_report", write_final_report)  # Deep Agent

# Add edges
full_builder.add_edge(START, "advisor")
full_builder.add_conditional_edges("advisor", route_after_advisor)
full_builder.add_edge("supervisor", "write_report")
full_builder.add_edge("write_report", END)

# Compile
deep_research_agent = full_builder.compile()

