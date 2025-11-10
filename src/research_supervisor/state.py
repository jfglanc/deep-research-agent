"""State schema for multi-agent research supervisor.

This module defines the state used by the research supervisor (Level 2),
which coordinates multiple research agents working on sub-topics in parallel.
"""

from typing_extensions import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
import operator


class SupervisorState(TypedDict):
    """State for research supervisor (Level 2).
    
    Coordinates multiple research agents working on sub-topics in parallel.
    
    Shared keys (passed to/from main graph):
    - research_topic
    - research_scope
    - notes
    - raw_notes
    
    Private keys (supervisor only):
    - supervisor_messages
    - research_iterations
    """
    
    # Supervisor's message history (private - NOT shared with sub-agents or main graph)
    supervisor_messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # From advisor: High-level topic (SHARED with main graph)
    # Example: "AI Impact on Software Engineering Jobs"
    research_topic: str
    
    # From advisor: Detailed scope (SHARED with main graph)
    # Example: "Research hiring changes, skill requirements, junior vs senior impact..."
    research_scope: str
    
    # Compressed findings from ALL sub-agents (SHARED with main graph)
    # Accumulated via operator.add as sub-agents complete
    notes: Annotated[list[str], operator.add]
    
    # Iteration counter (private to supervisor)
    # Tracks how many times supervisor has called tools (think_tool + ConductResearch)
    research_iterations: int
    
    # Raw findings from ALL sub-agents (SHARED with main graph)
    # Accumulated via operator.add as sub-agents complete
    raw_notes: Annotated[list[str], operator.add]

