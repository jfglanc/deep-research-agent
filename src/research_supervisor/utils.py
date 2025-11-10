"""Utility functions for research supervisor.

This module provides helper functions for the supervisor to:
1. Extract research findings from ToolMessages
2. Format research instructions for sub-agents
"""

from langchain_core.messages import BaseMessage, filter_messages


def get_notes_from_tool_calls(messages: list[BaseMessage]) -> list[str]:
    """Extract research notes from ToolMessage objects in supervisor message history.
    
    This function retrieves the compressed research findings that sub-agents
    return as ToolMessage content. When the supervisor delegates research to
    sub-agents via ConductResearch tool calls, each sub-agent returns its
    compressed findings as the content of a ToolMessage. This function
    extracts all such ToolMessage content to compile the final research notes.
    
    Args:
        messages: List of messages from supervisor's conversation history
        
    Returns:
        List of research note strings extracted from ToolMessage objects
    """
    return [
        tool_msg.content 
        for tool_msg in filter_messages(messages, include_types="tool")
    ]


def format_research_instructions(subtopic: str, questions: list[str]) -> str:
    """Format subtopic and questions into HumanMessage content for research agent.
    
    This creates the initial message that the research agent receives.
    
    IMPORTANT: The agent is NOT told it's a "subtopic" - just sees it as "topic".
    This maintains context isolation (agent doesn't know it's part of larger research).
    
    Args:
        subtopic: The specific research focus area
        questions: List of specific questions to answer
        
    Returns:
        Formatted string for HumanMessage content
        
    Example:
        format_research_instructions(
            "OpenAI Deep Research pricing",
            ["What are the pricing tiers?", "How does it compare to competitors?"]
        )
        
        Returns:
        '''Research the following topic:
        
        **Topic**: OpenAI Deep Research pricing
        
        **Research Questions to Answer**:
        1. What are the pricing tiers?
        2. How does it compare to competitors?
        
        Please conduct thorough research to answer these questions.'''
    """
    # Format questions as numbered list
    questions_formatted = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
    
    return f"""Research the following topic:

**Topic**: {subtopic}

**Research Questions to Answer**:
{questions_formatted}

Please conduct thorough research to answer these questions."""

