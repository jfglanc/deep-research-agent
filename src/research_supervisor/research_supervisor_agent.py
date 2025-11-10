"""Multi-agent research supervisor (Level 2).

This module implements a supervisor pattern where:
1. A supervisor agent coordinates research activities and delegates tasks
2. Multiple researcher agents work on specific sub-topics independently in parallel
3. Results are aggregated and compressed for final reporting

The supervisor uses parallel research execution to improve efficiency while
maintaining isolated context windows for each research topic.
"""

import asyncio
from typing_extensions import Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    HumanMessage,
    BaseMessage,
    SystemMessage,
    ToolMessage
)
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command

from src.research_supervisor.state import SupervisorState
from src.research_supervisor.tools import ConductResearch, ResearchComplete
from src.research_supervisor.prompts import SUPERVISOR_PROMPT
from src.research_supervisor.utils import (
    get_notes_from_tool_calls,
    format_research_instructions
)
from src.research_agent.research_agent import researcher_agent
from src.shared.utils import think_tool, get_today_str


# ===== CONFIGURATION =====

supervisor_tools = [ConductResearch, ResearchComplete, think_tool]
supervisor_model = ChatOpenAI(model="gpt-5-mini", temperature=0)
supervisor_model_with_tools = supervisor_model.bind_tools(supervisor_tools)

# System constants
max_researcher_iterations = 6  # Max total tool calls (think_tool + ConductResearch)
max_concurrent_researchers = 3  # Max parallel sub-agents


# ===== SUPERVISOR NODES =====

async def supervisor(state: SupervisorState) -> Command[Literal["supervisor_tools"]]:
    """Coordinate research activities (decision maker).
    
    Analyzes the research topic and scope to decide:
    - What research subtopics need investigation
    - What specific questions each sub-agent should answer
    - Whether to conduct parallel research
    - When research is complete
    
    Args:
        state: Current supervisor state with messages and research progress
        
    Returns:
        Command to proceed to supervisor_tools node with updated state
    """
    supervisor_messages = state.get("supervisor_messages", [])
    
    # Prepare system message with research topic, scope, and constraints
    system_message = SUPERVISOR_PROMPT.format(
        research_topic=state["research_topic"],
        research_scope=state["research_scope"],
        date=get_today_str(),
        max_concurrent_research_units=max_concurrent_researchers,
        max_researcher_iterations=max_researcher_iterations
    )
    
    messages = [SystemMessage(content=system_message)] + supervisor_messages
    
    # LLM makes decision about next research steps
    response = await supervisor_model_with_tools.ainvoke(messages)
    
    return Command(
        goto="supervisor_tools",  # ALWAYS go to tools for execution
        update={
            "supervisor_messages": [response],
            "research_iterations": state.get("research_iterations", 0) + 1
        }
    )


async def supervisor_tools(state: SupervisorState) -> Command[Literal["supervisor", "__end__"]]:
    """Execute supervisor decisions (executor and controller).
    
    Handles:
    - Executing think_tool calls for strategic reflection
    - Launching parallel research agents for different topics
    - Aggregating research results
    - Determining when research is complete
    
    Args:
        state: Current supervisor state with messages and iteration count
        
    Returns:
        Command to continue supervision, end process, or handle errors
    """
    supervisor_messages = state.get("supervisor_messages", [])
    research_iterations = state.get("research_iterations", 0)
    most_recent_message = supervisor_messages[-1]
    
    # Initialize variables for single return pattern
    tool_messages = []
    all_raw_notes = []
    next_step = "supervisor"  # Default: loop back to supervisor
    should_end = False
    
    # ===== CHECK TERMINATION CONDITIONS =====
    exceeded_iterations = research_iterations >= max_researcher_iterations
    no_tool_calls = not most_recent_message.tool_calls
    research_complete = any(
        tool_call["name"] == "ResearchComplete"
        for tool_call in most_recent_message.tool_calls
    )
    
    if exceeded_iterations or no_tool_calls or research_complete:
        should_end = True
        next_step = END
    
    else:
        # ===== EXECUTE TOOLS =====
        try:
            # Separate think_tool calls from ConductResearch calls
            think_tool_calls = [
                tool_call for tool_call in most_recent_message.tool_calls
                if tool_call["name"] == "think_tool"
            ]
            
            conduct_research_calls = [
                tool_call for tool_call in most_recent_message.tool_calls
                if tool_call["name"] == "ConductResearch"
            ]
            
            # Execute think_tool (synchronous)
            for tool_call in think_tool_calls:
                observation = think_tool.invoke(tool_call["args"])
                tool_messages.append(
                    ToolMessage(
                        content=observation,
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"]
                    )
                )
            
            # Execute ConductResearch (asynchronous, parallel)
            if conduct_research_calls:
                # Create coroutines for parallel execution
                # Each coroutine invokes a research agent with specific instructions
                coros = [
                    researcher_agent.ainvoke({
                        "researcher_messages": [
                            HumanMessage(content=format_research_instructions(
                                tool_call["args"]["research_subtopic"],
                                tool_call["args"]["research_questions"]  # list[str]
                            ))
                        ],
                        "research_subtopic": tool_call["args"]["research_subtopic"],
                        "research_questions": tool_call["args"]["research_questions"]
                    })
                    for tool_call in conduct_research_calls
                ]
                
                # Execute ALL sub-agents in parallel
                tool_results = await asyncio.gather(*coros)
                
                # Extract compressed research → ToolMessages for supervisor
                for result, tool_call in zip(tool_results, conduct_research_calls):
                    tool_messages.append(
                        ToolMessage(
                            content=result.get("compressed_research", "Error synthesizing research"),
                            name="ConductResearch",
                            tool_call_id=tool_call["id"]
                        )
                    )
                
                # Collect raw notes from all sub-agents
                all_raw_notes = [
                    "\n".join(result.get("raw_notes", []))
                    for result in tool_results
                ]
        
        except Exception as e:
            print(f"Error in supervisor tools: {e}")
            should_end = True
            next_step = END
    
    # ===== SINGLE RETURN POINT =====
    if should_end:
        return Command(
            goto=next_step,
            update={
                # Extract all ToolMessage contents as notes
                "notes": get_notes_from_tool_calls(supervisor_messages),
                # MUST pass through shared keys (or they're lost to parent graph)
                "research_topic": state["research_topic"],
                "research_scope": state["research_scope"]
                # raw_notes already accumulated via operator.add during loop
            }
        )
    else:
        return Command(
            goto=next_step,  # Loop back to supervisor
            update={
                "supervisor_messages": tool_messages,
                "raw_notes": all_raw_notes
            }
        )


# ===== GRAPH CONSTRUCTION =====

# Build supervisor graph
supervisor_builder = StateGraph(SupervisorState)
supervisor_builder.add_node("supervisor", supervisor)
supervisor_builder.add_node("supervisor_tools", supervisor_tools)
supervisor_builder.add_edge(START, "supervisor")
# NOTE: No edges between supervisor and supervisor_tools!
# Routing is done via Command returns

supervisor_agent = supervisor_builder.compile()

