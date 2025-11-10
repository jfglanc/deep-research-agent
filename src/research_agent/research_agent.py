"""Individual research agent implementation (Level 3).

This module implements a research agent that executes focused searches on a specific
subtopic with specific research questions. The agent is invoked by the supervisor
and has no awareness of the parent research or other parallel agents.

Receives from supervisor via initial HumanMessage:
- Research topic (NOT called "subtopic" to agent)
- Research questions (formatted as numbered list)

State fields (from supervisor):
- research_subtopic: str
- research_questions: list[str]

Returns to supervisor:
- compressed_research: Clean findings
- raw_notes: All searches
"""

from typing_extensions import Literal

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, filter_messages
from langchain_openai import ChatOpenAI

from src.research_agent.state import ResearcherState
from src.research_agent.prompts import (
    RESEARCH_AGENT_PROMPT,
    COMPRESS_RESEARCH_SYSTEM_PROMPT,
    COMPRESS_RESEARCH_HUMAN_MESSAGE
)
from src.research_agent.tools import tavily_search
from src.shared.utils import think_tool, get_today_str


# ===== CONFIGURATION =====

# Initialize models
research_model = ChatOpenAI(model="gpt-5", temperature=0)
compression_model = ChatOpenAI(model="gpt-5-mini", temperature=0)

# Set up tools
tools = [tavily_search, think_tool]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = research_model.bind_tools(tools)


# ===== AGENT NODES =====

async def llm_call(state: ResearcherState):
    """LLM decides what to search next or when to stop.
    
    The system prompt is GENERIC and does NOT include subtopic/questions.
    Those come from the initial HumanMessage when the graph is invoked.
    
    Returns:
        State update with LLM response
    """
    # System prompt does NOT include subtopic/questions
    # (Those are in the initial HumanMessage from supervisor)
    system_message = SystemMessage(content=RESEARCH_AGENT_PROMPT.format(
        date=get_today_str()
    ))
    
    messages = [system_message] + list(state["researcher_messages"])
    
    response = await model_with_tools.ainvoke(messages)
    
    return {"researcher_messages": [response]}


async def tool_node(state: ResearcherState):
    """Execute tools called by the LLM.
    
    Handles both think_tool (reflection) and tavily_search (web search).
    Collects raw_notes from search results for traceability.
    
    Returns:
        State update with tool execution results
    """
    last_message = state["researcher_messages"][-1]
    tool_messages = []
    raw_notes_updates = []
    
    for tool_call in last_message.tool_calls:
        # Execute the appropriate tool
        tool = tools_by_name[tool_call["name"]]
        observation = await tool.ainvoke(tool_call["args"])
        
        # Collect raw notes (only from searches, not think_tool)
        if tool_call["name"] == "tavily_search":
            raw_notes_updates.append(observation)
        
        # Create tool message
        tool_messages.append(ToolMessage(
            content=observation,
            name=tool_call["name"],
            tool_call_id=tool_call["id"]
        ))
    
    return {
        "researcher_messages": tool_messages,
        "raw_notes": raw_notes_updates
    }


async def compress_research(state: ResearcherState):
    """Compress ALL research findings into clean summary.
    
    This is the FINAL node after the agent loop ends.
    Takes all messages (which include initial HumanMessage with subtopic/questions)
    and compresses into a clean, comprehensive summary.
    
    Returns:
        State update with compressed research
    """
    system_message = SystemMessage(content=COMPRESS_RESEARCH_SYSTEM_PROMPT.format(
        date=get_today_str()
    ))
    
    # All messages from research loop (includes initial HumanMessage with subtopic/questions)
    messages = [system_message] + list(state["researcher_messages"])
    
    # Reinforce task at end (helpful for long contexts)
    # Note: No need to repeat subtopic/questions - they're in the initial message
    messages.append(HumanMessage(content=COMPRESS_RESEARCH_HUMAN_MESSAGE))
    
    response = await compression_model.ainvoke(messages)
    
    return {"compressed_research": response.content}


# ===== ROUTING LOGIC =====

def should_continue(state: ResearcherState) -> Literal["tool_node", "compress_research"]:
    """Determine whether to continue research loop or compress findings.
    
    If LLM called tools, continue to tool execution.
    If LLM provided answer (no tool calls), compress research.
    
    Returns:
        "tool_node": Continue to tool execution
        "compress_research": Stop and compress all findings
    """
    last_message = state["researcher_messages"][-1]
    
    if last_message.tool_calls:
        return "tool_node"  # More searches needed
    
    return "compress_research"  # Done, compress everything


# ===== GRAPH CONSTRUCTION =====

# Build the research agent workflow
research_builder = StateGraph(ResearcherState)

# Add nodes
research_builder.add_node("llm_call", llm_call)
research_builder.add_node("tool_node", tool_node)
research_builder.add_node("compress_research", compress_research)

# Add edges
research_builder.add_edge(START, "llm_call")
research_builder.add_conditional_edges("llm_call", should_continue)
research_builder.add_edge("tool_node", "llm_call")  # Loop back
research_builder.add_edge("compress_research", END)  # Terminal

# Compile the agent
researcher_agent = research_builder.compile()

