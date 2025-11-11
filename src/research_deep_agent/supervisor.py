"""Deep Agent supervisor for research coordination.

This module creates the supervisor deep agent and provides a wrapper
function for integration with the main graph.
"""

from deepagents import create_deep_agent
from langchain_core.messages import HumanMessage

from src.state import FullResearchState
from src.config import RESEARCH_SUPERVISOR_CONFIG
from src.research_deep_agent.researcher_subagent import research_subagent
from src.research_deep_agent.prompts import SUPERVISOR_SYSTEM_PROMPT, SUPERVISOR_INITIAL_MESSAGE_TEMPLATE


# ===== CREATE SUPERVISOR DEEP AGENT =====
# Created ONCE at module import (efficient, reusable)

supervisor_deep_agent = create_deep_agent(
    model=RESEARCH_SUPERVISOR_CONFIG["model"],  # claude-sonnet-4-5-20250929
    tools=[],  # Supervisor only delegates, no custom tools
    system_prompt=SUPERVISOR_SYSTEM_PROMPT,  # General instructions (no topic/scope)
    subagents=[research_subagent],  # Can spawn research-agent subagents
    # backend defaults to StateBackend (virtual filesystem in state["files"])
)


# ===== WRAPPER FUNCTION FOR MAIN GRAPH =====

async def deep_research_supervisor(state: FullResearchState) -> dict:
    """Wrapper function to integrate Deep Agent supervisor into main graph.
    
    Receives FullResearchState from advisor, invokes Deep Agent supervisor,
    returns updated state for report writer.
    
    Args:
        state: State from main graph containing research_topic and research_scope
        
    Returns:
        Updated state with files populated and supervisor's final message
    """
    
    # Prepare initial message with research topic and scope
    initial_message = HumanMessage(
        content=SUPERVISOR_INITIAL_MESSAGE_TEMPLATE.format(
            research_topic=state["research_topic"],
            research_scope=state["research_scope"]
        )
    )
    
    # Invoke deep agent with selective fields (clean separation)
    result = await supervisor_deep_agent.ainvoke({
        "messages": [initial_message],  # Fresh message list for supervisor
        "files": state.get("files", {}),  # Empty initially, will be populated
        "todos": state.get("todos", [])   # Empty initially
    })
    
    # Return selective fields to main graph
    return {
        "files": result["files"],  # All research files created by subagents + index
        "messages": [result["messages"][-1]],  # Only supervisor's final summary message
        # Pass through unchanged fields (required for report writer)
        "research_topic": state["research_topic"],
        "research_scope": state["research_scope"]
    }

