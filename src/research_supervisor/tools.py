"""Tools for research supervisor.

This module defines the tools used by the supervisor to delegate research
to sub-agents and signal research completion.
"""

from pydantic import BaseModel, Field
from langchain_core.tools import tool


@tool
class ConductResearch(BaseModel):
    """Delegate research to a specialized sub-agent.
    
    The supervisor generates specific instructions for each sub-agent,
    including a focused subtopic and a list of research questions.
    
    This is a RICHER schema than the course implementation:
    - research_subtopic: Focused area (string)
    - research_questions: List of specific questions (list[str])
    - max_searches: Configurable search budget (int)
    """
    
    research_subtopic: str = Field(
        description="The specific subtopic for this sub-agent to research. Should be focused and distinct from other sub-agents. Example: 'OpenAI Deep Research product features'"
    )
    
    research_questions: list[str] = Field(
        description="List of 2-4 specific research questions for this sub-agent to answer. Each question should be clear and targeted. Example: ['What are the key features?', 'How does pricing work?', 'What are user reviews?']"
    )
    
    max_searches: int = Field(
        default=5,
        description="Maximum number of searches this sub-agent should perform. Adjust based on subtopic complexity: 2-3 for simple, 4-5 for complex."
    )


@tool
class ResearchComplete(BaseModel):
    """Signal that research coordination is complete.
    
    The supervisor calls this tool when it has gathered comprehensive
    findings from all necessary sub-agents and is ready to end research.
    """
    pass

