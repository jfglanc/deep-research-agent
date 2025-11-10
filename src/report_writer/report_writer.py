"""Report writer for final research report generation.

This module provides the node that generates the final research report
from the accumulated findings from all research sub-agents.
"""

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage

from src.report_writer.prompts import FINAL_REPORT_PROMPT
from src.shared.utils import get_today_str
from src.shared.state import FullResearchState


# ===== CONFIGURATION =====

writer_model = init_chat_model(model="openai:gpt-4.1", max_tokens=32000)


# ===== REPORT WRITER NODE =====

async def write_final_report(state: FullResearchState):
    """Generate final research report from supervisor's findings.
    
    Synthesizes all research findings into a comprehensive final report
    with proper structure, citations, and analysis.
    
    Reads from state:
    - research_topic: High-level subject
    - research_scope: Detailed instructions
    - notes: List of compressed findings from sub-agents
    
    Writes to state:
    - final_report: Complete markdown report
    - messages: AIMessage with the report for user display
    
    Args:
        state: Current full research state
        
    Returns:
        State update with final report
    """
    # Join all findings from sub-agents
    findings = "\n\n".join(state["notes"])
    
    # Format prompt with all context
    prompt = FINAL_REPORT_PROMPT.format(
        research_topic=state["research_topic"],
        research_scope=state["research_scope"],
        findings=findings,
        date=get_today_str()
    )
    
    # Generate report
    response = await writer_model.ainvoke([HumanMessage(content=prompt)])
    
    return {
        "final_report": response.content,
        "messages": [AIMessage(content=f"Here is your research report:\n\n{response.content}")]
    }

