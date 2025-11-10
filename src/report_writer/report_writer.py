"""Deep Agent report writer for final research report generation.

Reads research findings from virtual filesystem and synthesizes
comprehensive markdown report.
"""

from deepagents import create_deep_agent
from langchain_core.messages import HumanMessage, AIMessage

from src.state import FullResearchState
from src.config import REPORT_WRITER_CONFIG
from src.report_writer.prompts import (
    REPORT_WRITER_SYSTEM_PROMPT,
    REPORT_WRITER_INITIAL_MESSAGE_TEMPLATE
)


# ===== CREATE REPORT WRITER DEEP AGENT =====
# Created ONCE at module import (efficient, reusable)

report_writer_agent = create_deep_agent(
    model=REPORT_WRITER_CONFIG["model"],  # claude-sonnet-4-5-20250929
    tools=[],  # No custom tools, just file system tools from middleware
    system_prompt=REPORT_WRITER_SYSTEM_PROMPT,  # Single comprehensive format
    subagents=[]  # No subagents needed
)


# ===== WRAPPER FUNCTION FOR MAIN GRAPH =====

async def write_final_report(state: FullResearchState) -> dict:
    """Generate final research report using Deep Agent.
    
    Reads research findings from state["files"] and synthesizes
    into comprehensive markdown report.
    
    Args:
        state: State from supervisor containing research_topic, research_scope,
               files (all research findings), and supervisor's summary message
               
    Returns:
        Updated state with final_report field populated and report in message
    """
    
    # Extract supervisor's summary from last message
    supervisor_summary = state["messages"][-1].content if state["messages"] else "Research completed."
    
    # Prepare initial message with all context
    initial_message = HumanMessage(
        content=REPORT_WRITER_INITIAL_MESSAGE_TEMPLATE.format(
            research_topic=state["research_topic"],
            research_scope=state["research_scope"],
            supervisor_summary=supervisor_summary
        )
    )
    
    # Invoke deep agent with files from supervisor
    result = await report_writer_agent.ainvoke({
        "messages": [initial_message],
        "files": state.get("files", {}),  # All research files
        "todos": []  # Fresh todos for report writer's planning
    })
    
    # Extract final report from last message
    final_report_content = result["messages"][-1].content
    
    # Return report in both final_report field and message
    return {
        "final_report": final_report_content,
        "messages": [AIMessage(content=f"Here's your research report:\n\n{final_report_content}")]
    }
