## Deep Research Agent - Main Graph

from typing_extensions import Literal, Annotated
import operator

from langgraph.graph import StateGraph, START, END, MessagesState

# State for the main graph
from src.state import FullResearchState

# Research advisor and research supervisor imported as compiled graphs to be used as nodes
from src.advisor.advisor_agent import advisor_agent
from src.research_supervisor.research_supervisor_agent import supervisor_agent

# Report writer node is a simple node that writes the final report
from src.report_writer.report_writer import write_final_report


# ===== ROUTING LOGIC =====

# If the user approved the research, route to the research supervisor
# If the user is still defining the scope with the advisor, end the graph
def route_after_advisor(state: FullResearchState) -> Literal["supervisor", "__end__"]:
    if state.get("user_approved"):
        return "supervisor"
    return END


# ===== GRAPH CONSTRUCTION =====

# StateGraph instance
full_builder = StateGraph(FullResearchState)

# Nodes
full_builder.add_node("advisor", advisor_agent)              # Advisor subgraph as a node
full_builder.add_node("supervisor", supervisor_agent)         # Supervisor subgraph as a node
full_builder.add_node("write_report", write_final_report)     # Report writer function

# Edges
full_builder.add_edge(START, "advisor")
full_builder.add_conditional_edges("advisor", route_after_advisor)
full_builder.add_edge("supervisor", "write_report")
full_builder.add_edge("write_report", END)

# Compiled main graph
deep_research_agent = full_builder.compile()

