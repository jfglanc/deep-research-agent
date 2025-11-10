# Implementation Roadmap: Deep Research System
**YOUR CUSTOM ARCHITECTURE - Based on Design Decisions**

---

## 📍 Current Status

### ✅ Phase 0: Research Advisor (COMPLETE)

**Files**: 
- `advisor/advisor_agent.py` (renamed from `graph.py`)
- `advisor/prompts.py` (renamed from `advisor_prompt.py`)

**What it does**:
- Interactive conversational agent helping users define research direction
- Can search the web during scoping for current/niche topics
- Proposes 2-3 research directions based on conversation
- Confirms with user before proceeding
- Captures structured output via `execute_research` tool call

**Graph flow**:
```
START → call_model ↔ tool_node → save_research_brief → END
                       ↑               ↓
                       └───────────────┘
```

**Outputs to main graph**:
- `research_topic`: High-level subject (e.g., "AI Impact on SWE Jobs")
- `research_scope`: Detailed instructions (e.g., "Research hiring changes, skill requirements...")
- `user_approved`: Boolean (True when execute_research is called)
- `messages`: Full conversation history

---

## 🏗️ YOUR CONFIRMED ARCHITECTURE

### **Three-Level Graph Hierarchy**

```
┌─────────────────────────────────────────────────────────────────────┐
│ LEVEL 1: MAIN GRAPH                                                 │
│ File: deep_research_agent.py (top-level orchestration)              │
│                                                                     │
│  ┌──────────────┐   ┌─────────────────┐   ┌──────────────┐        │
│  │   Advisor    │ → │    Research     │ → │    Report    │ →  END │
│  │  (Subgraph)  │   │   Supervisor    │   │    Writer    │        │
│  │  advisor/    │   │   (Subgraph)    │   │  report_     │        │
│  │              │   │   research_     │   │  writer/     │        │
│  │              │   │   supervisor/   │   │              │        │
│  └──────────────┘   └────────┬────────┘   └──────────────┘        │
│                              │                                     │
│   Passes: research_topic,    │                                     │
│           research_scope     │                                     │
│                              ↓                                     │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │ LEVEL 2: SUPERVISOR GRAPH                                │     │
│  │ File: research_supervisor/research_supervisor_agent.py   │     │
│  │                                                          │     │
│  │  ┌────────────┐         ┌──────────────────┐            │     │
│  │  │ supervisor │    ↔    │ supervisor_tools │            │     │
│  │  │ (decides)  │         │   (executes)     │            │     │
│  │  └────────────┘         └────────┬─────────┘            │     │
│  │                                  │                       │     │
│  │  Knows: research_topic,          ↓                       │     │
│  │         research_scope     Creates for each:             │     │
│  │                            - research_subtopic           │     │
│  │                            - research_questions (List)   │     │
│  │                                  │                       │     │
│  │  ┌───────────────────────────────┴──────────────────┐   │     │
│  │  │ LEVEL 3: RESEARCH AGENTS                         │   │     │
│  │  │ File: research_agent/research_agent.py           │   │     │
│  │  │ (Invoked as tools via ConductResearch)           │   │     │
│  │  │                                                  │   │     │
│  │  │  ┌──────────────────────┐                        │   │     │
│  │  │  │ Research Agent 1     │  Initial HumanMessage: │   │     │
│  │  │  │                      │  "Research: {subtopic} │   │     │
│  │  │  │ llm_call ↔ tool_node │   Questions:           │   │     │
│  │  │  │     ↓                │   1. {q1}              │   │     │
│  │  │  │ compress_research    │   2. {q2}"             │   │     │
│  │  │  └──────────────────────┘                        │   │     │
│  │  │  NO awareness of parent research                 │   │     │
│  │  │                                                  │   │     │
│  │  │  ┌──────────────────────┐   (PARALLEL)           │   │     │
│  │  │  │ Research Agent 2     │                        │   │     │
│  │  │  └──────────────────────┘                        │   │     │
│  │  │                                                  │   │     │
│  │  │  ┌──────────────────────┐   (PARALLEL)           │   │     │
│  │  │  │ Research Agent 3     │                        │   │     │
│  │  │  └──────────────────────┘                        │   │     │
│  │  │                                                  │   │     │
│  │  │  Returns: compressed_research, raw_notes         │   │     │
│  │  └──────────────────────────────────────────────────┘   │     │
│  │                                                          │     │
│  │  Returns to main: notes (list), raw_notes (list)         │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                     │
│  Passes to writer: research_topic, research_scope, notes           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ✅ YOUR CONFIRMED DESIGN DECISIONS

### **Architecture**
- ✅ Three-level graph hierarchy (main → supervisor → research agents)
- ✅ Supervisor is MANDATORY (always used, even for single topics)
- ✅ Research agents invoked as tools via `ConductResearch`
- ✅ Max 3 concurrent researchers

### **State Management**
- ✅ Layered state schemas (different schemas per graph level)
- ✅ NO `research_brief` field (use `research_topic` + `research_scope`)
- ✅ Supervisor knows: `research_topic`, `research_scope`
- ✅ Sub-agents know: `research_subtopic`, `research_questions` (generated by supervisor)

### **Tools & Control**
- ✅ Richer `ConductResearch` tool schema (supervisor controls sub-agent behavior)
- ✅ `ResearchComplete` tool (supervisor signals done)
- ✅ `think_tool` after EACH search (mandatory in prompts)

### **Compression**
- ✅ `compress_research` node AFTER agent loop ends (final node)

### **Termination**
- ✅ LLM decides when to stop (no explicit ResearchDone tool for sub-agents)

### **Prompting**
- ✅ Explicit pattern detection for supervisor delegation
- ✅ Supervisor generates specific research questions for each sub-agent
- ✅ Questions passed as **list[str]** (structured, easier to parse)
- ✅ Sub-agents receive instructions via **HumanMessage** (not system prompt)

### **Report Generation**
- ✅ Simple template-based (can enhance later)

### **Key Innovation**
- ✅ `research_questions` as `list[str]` instead of single string
- ✅ `format_research_instructions()` helper formats questions as numbered list
- ✅ Sub-agent thinks it's researching a "topic" (not aware it's a "subtopic")

---

## ❌ REMAINING IMPLEMENTATION TASKS

### **Phase 1: Research Agent** 🔴 (HIGH PRIORITY)

**File**: `my_implementation/research_agent.py`

#### State Schema (YOUR DESIGN)

```python
from typing_extensions import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
import operator

class ResearcherState(TypedDict):
    """State for individual research agent.
    
    CRITICAL: This agent is invoked by supervisor with ISOLATED context.
    It has NO awareness of:
    - Parent research_topic or research_scope
    - Other parallel sub-agents
    - Why this research is being conducted
    
    It ONLY knows what the supervisor tells it:
    - research_subtopic: Specific focus area
    - research_questions: List of specific questions to answer
    """
    
    # Private message history (ISOLATED from supervisor and other agents)
    researcher_messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # Supervisor-provided: Specific subtopic for THIS agent
    # Example: "OpenAI Deep Research product features and capabilities"
    research_subtopic: str
    
    # Supervisor-provided: List of specific questions to answer
    # Example: ["What are the key features?", "How does pricing work?", "What are user reviews?"]
    research_questions: list[str]
    
    # Final output: Compressed research findings
    compressed_research: str
    
    # Raw search results (for debugging/traceability)
    raw_notes: Annotated[list[str], operator.add]
```

#### Tools (YOUR DESIGN - With think_tool after EACH search)

```python
# Tavily search tool
@tool(parse_docstring=True)
def tavily_search(query: str) -> str:
    """Search the web for information.
    
    Args:
        query: A specific, targeted search query.
    
    Returns:
        Summarized search results.
    """
    # Implementation similar to your search_web
    results = tavily_client.search(query, max_results=5)
    summary = summarize_results(results)  # Compress
    return summary

# Think tool (from course)
from deep_research_from_scratch.utils import think_tool
```

#### Nodes

**llm_call**:
```python
async def llm_call(state: ResearcherState):
    """LLM decides next search or when to stop."""
    
    # System prompt does NOT include subtopic/questions
    # (Those come from initial HumanMessage when graph is invoked)
    system_message = SystemMessage(content=RESEARCH_AGENT_PROMPT.format(
        date=get_today_str()
    ))
    
    messages = [system_message] + list(state["researcher_messages"])
    
    # Bind tools
    tools = [tavily_search, think_tool]
    model_with_tools = research_model.bind_tools(tools)
    
    response = await model_with_tools.ainvoke(messages)
    return {"researcher_messages": [response]}
```

**tool_node**:
```python
async def tool_node(state: ResearcherState):
    """Execute tools with raw note collection."""
    
    last_message = state["researcher_messages"][-1]
    tool_messages = []
    raw_notes_updates = []
    
    for tool_call in last_message.tool_calls:
        if tool_call["name"] == "think_tool":
            observation = think_tool.invoke(tool_call["args"])
        else:  # tavily_search
            observation = tavily_search.invoke(tool_call["args"])
            raw_notes_updates.append(observation)  # Collect raw
        
        tool_messages.append(ToolMessage(
            content=observation,
            name=tool_call["name"],
            tool_call_id=tool_call["id"]
        ))
    
    return {
        "researcher_messages": tool_messages,
        "raw_notes": raw_notes_updates
    }
```

**compress_research** (FINAL node after loop):
```python
async def compress_research(state: ResearcherState):
    """Compress ALL research into clean summary."""
    
    system_message = SystemMessage(content=COMPRESS_RESEARCH_PROMPT.format(
        date=get_today_str()
    ))
    
    # All messages from research loop (includes initial HumanMessage with subtopic/questions)
    messages = [system_message] + list(state["researcher_messages"])
    
    # Reinforce task at end (for long contexts)
    # Note: No need to repeat subtopic/questions - they're in the initial message
    messages.append(HumanMessage(content="Compress ALL findings above into a clean summary."))
    
    response = await compression_model.ainvoke(messages)
    return {"compressed_research": response.content}
```

#### Graph Construction

```python
def should_continue(state: ResearcherState) -> Literal["tool_node", "compress_research"]:
    """LLM decides: continue searching OR compress findings."""
    last_message = state["researcher_messages"][-1]
    
    if last_message.tool_calls:
        return "tool_node"  # More searches needed
    return "compress_research"  # Done, compress everything

# Build graph
research_builder = StateGraph(ResearcherState)
research_builder.add_node("llm_call", llm_call)
research_builder.add_node("tool_node", tool_node)
research_builder.add_node("compress_research", compress_research)

research_builder.add_edge(START, "llm_call")
research_builder.add_conditional_edges("llm_call", should_continue)
research_builder.add_edge("tool_node", "llm_call")  # Loop back
research_builder.add_edge("compress_research", END)  # Terminal

researcher_agent = research_builder.compile()
```

#### Required Prompts

**RESEARCH_AGENT_PROMPT**:
```
You are a research agent. Your job is to answer the research questions provided in the conversation.

<Available Tools>
1. tavily_search: Search the web for information
2. think_tool: Reflect on findings and plan next steps

**CRITICAL**: Use think_tool after EACH search to:
- Assess what you learned from the search
- Identify information gaps
- Determine if you need more searches
- Plan your next search query (if needed)

</Available Tools>

<Instructions>
1. Read the research questions carefully
2. Start with broader searches
3. After EACH search, use think_tool to reflect
4. Progressively narrow your searches to fill gaps
5. Stop when you can answer all research questions comprehensively
</Instructions>

<Hard Limits>
- Max 5 tavily_search calls
- MUST use think_tool after each search
- Stop when research questions are answered OR max searches reached
</Hard Limits>

Today's date: {date}
```

**COMPRESS_RESEARCH_PROMPT**: (Use from course `prompts.py`)

**IMPORTANT**: The research subtopic and questions are passed in the **initial HumanMessage**, NOT in the system prompt. Example:

```python
researcher_messages = [
    HumanMessage(content="""
    Research the following subtopic:
    **Subtopic**: OpenAI Deep Research product
    
    **Research Questions**:
    1. What are the key features?
    2. How does pricing work?
    3. What do user reviews say?
    """)
]
```

---

### **Phase 2: Multi-Agent Supervisor** 🔴 (HIGH PRIORITY - MANDATORY)

**File**: `my_implementation/supervisor.py`

**IMPORTANT**: This is NOT optional in your architecture.

#### Supervisor State Schema (YOUR DESIGN)

```python
from typing_extensions import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from langchain_core.tools import tool
import operator

class SupervisorState(TypedDict):
    """State for research supervisor.
    
    Coordinates multiple research agents working on sub-topics in parallel.
    """
    
    # Supervisor's message history (private - NOT shared with sub-agents)
    supervisor_messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # From advisor: High-level topic (SHARED with main graph)
    research_topic: str
    
    # From advisor: Detailed scope (SHARED with main graph)
    research_scope: str
    
    # Compressed findings from ALL sub-agents (SHARED with main graph)
    notes: Annotated[list[str], operator.add]
    
    # Iteration counter (private to supervisor)
    research_iterations: int
    
    # Raw findings from ALL sub-agents (SHARED with main graph)
    raw_notes: Annotated[list[str], operator.add]
```

#### Tools (YOUR RICHER SCHEMA)

```python
@tool
class ConductResearch(BaseModel):
    """Delegate research to a specialized sub-agent.
    
    The supervisor generates specific instructions for each sub-agent.
    """
    
    research_subtopic: str = Field(
        description="The specific subtopic for this sub-agent to research. Should be focused and distinct from other sub-agents."
    )
    
    research_questions: list[str] = Field(
        description="List of specific research questions for this sub-agent to answer. Each question should be clear and targeted."
    )
    
    max_searches: int = Field(
        default=5,
        description="Maximum number of searches this sub-agent should perform. Adjust based on subtopic complexity."
    )

@tool
class ResearchComplete(BaseModel):
    """Signal that research coordination is complete."""
    pass
```

**KEY DIFFERENCES FROM COURSE**: 
- Course: `research_topic` (single string field)
- Yours: `research_subtopic` + `research_questions` (list!) + `max_searches` (richer control)
- Yours: Questions as **list** (better structured, easier to parse)

#### Supervisor Nodes

**supervisor node**:
```python
async def supervisor(state: SupervisorState) -> Command[Literal["supervisor_tools"]]:
    """Decide what research to delegate."""
    
    supervisor_messages = state.get("supervisor_messages", [])
    
    # System prompt with BOTH topic and scope
    system_message = lead_researcher_prompt.format(
        research_topic=state["research_topic"],
        research_scope=state["research_scope"],
        date=get_today_str(),
        max_concurrent_research_units=3,  # Your confirmed limit
        max_researcher_iterations=6
    )
    
    messages = [SystemMessage(content=system_message)] + supervisor_messages
    
    # Bind tools
    supervisor_model_with_tools = supervisor_model.bind_tools([
        ConductResearch,
        ResearchComplete,
        think_tool
    ])
    
    response = await supervisor_model_with_tools.ainvoke(messages)
    
    return Command(
        goto="supervisor_tools",  # ALWAYS go to tools
        update={
            "supervisor_messages": [response],
            "research_iterations": state.get("research_iterations", 0) + 1
        }
    )
```

**supervisor_tools node**:
```python
async def supervisor_tools(state: SupervisorState) -> Command[Literal["supervisor", "__end__"]]:
    """Execute supervisor's decisions (tools) and check termination."""
    
    supervisor_messages = state.get("supervisor_messages", [])
    research_iterations = state.get("research_iterations", 0)
    most_recent_message = supervisor_messages[-1]
    
    # Termination checks
    exceeded_iterations = research_iterations >= 6
    no_tool_calls = not most_recent_message.tool_calls
    research_complete = any(
        tc["name"] == "ResearchComplete" 
        for tc in most_recent_message.tool_calls
    )
    
    if exceeded_iterations or no_tool_calls or research_complete:
        # END supervisor graph
        return Command(
            goto=END,
            update={
                "notes": get_notes_from_tool_calls(supervisor_messages),
                # MUST pass through shared keys:
                "research_topic": state["research_topic"],
                "research_scope": state["research_scope"]
            }
        )
    
    # Separate tool types
    think_tool_calls = [
        tc for tc in most_recent_message.tool_calls 
        if tc["name"] == "think_tool"
    ]
    
    conduct_research_calls = [
        tc for tc in most_recent_message.tool_calls 
        if tc["name"] == "ConductResearch"
    ]
    
    tool_messages = []
    all_raw_notes = []
    
    # Execute think_tool (synchronous)
    for tc in think_tool_calls:
        observation = think_tool.invoke(tc["args"])
        tool_messages.append(ToolMessage(
            content=observation,
            name="think_tool",
            tool_call_id=tc["id"]
        ))
    
    # Execute ConductResearch (asynchronous, parallel)
    if conduct_research_calls:
        # YOUR DESIGN: Pass subtopic + questions (as list) to each sub-agent
        coros = [
            researcher_agent.ainvoke({
                "researcher_messages": [HumanMessage(content=format_research_instructions(
                    tc["args"]["research_subtopic"],
                    tc["args"]["research_questions"]  # This is a list[str]
                ))],
                "research_subtopic": tc["args"]["research_subtopic"],
                "research_questions": tc["args"]["research_questions"]
            })
            for tc in conduct_research_calls
        ]
        
        # Parallel execution
        tool_results = await asyncio.gather(*coros)
        
        # Extract compressed research → ToolMessages
        for result, tc in zip(tool_results, conduct_research_calls):
            tool_messages.append(ToolMessage(
                content=result.get("compressed_research", "Error"),
                name="ConductResearch",
                tool_call_id=tc["id"]
            ))
        
        # Collect raw notes
        all_raw_notes = [
            "\n".join(result.get("raw_notes", []))
            for result in tool_results
        ]
    
    # Continue loop
    return Command(
        goto="supervisor",
        update={
            "supervisor_messages": tool_messages,
            "raw_notes": all_raw_notes
        }
    )
```

#### Helper Functions

```python
def get_notes_from_tool_calls(messages: list[BaseMessage]) -> list[str]:
    """Extract compressed research from ToolMessages."""
    return [
        tool_msg.content 
        for tool_msg in filter_messages(messages, include_types="tool")
    ]

def format_research_instructions(subtopic: str, questions: list[str]) -> str:
    """Format subtopic and questions into HumanMessage content.
    
    This creates the initial message for the research agent.
    Agent is NOT told it's a "subtopic" - just receives research instructions.
    """
    questions_formatted = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
    
    return f"""Research the following topic:

**Topic**: {subtopic}

**Research Questions to Answer**:
{questions_formatted}

Please conduct thorough research to answer these questions.
"""
```

#### Graph Construction

```python
supervisor_builder = StateGraph(SupervisorState)
supervisor_builder.add_node("supervisor", supervisor)
supervisor_builder.add_node("supervisor_tools", supervisor_tools)
supervisor_builder.add_edge(START, "supervisor")

supervisor_agent = supervisor_builder.compile()
```

**Note**: No edges between supervisor nodes! Routing done via `Command`.

#### Required Prompts

**SUPERVISOR_PROMPT** (YOUR VERSION):
```
You are a research supervisor coordinating sub-agents.

Research Topic: {research_topic}
Research Scope: {research_scope}

<Task>
Analyze the research scope and decide:
1. How many sub-agents to spawn? (1-3 max)
2. For each sub-agent, define:
   - A specific subtopic (focused area of research)
   - A list of 2-4 research questions to answer
   - Max searches (2-5 based on complexity)

Call ConductResearch for each subtopic. Provide:
- research_subtopic: Clear focus area (string)
- research_questions: List of specific questions (list of strings)
- max_searches: Budget for this sub-agent (integer)

Example:
ConductResearch(
    research_subtopic="OpenAI Deep Research product features",
    research_questions=[
        "What are the core capabilities?",
        "How does pricing compare to competitors?",
        "What are notable strengths and weaknesses?"
    ],
    max_searches=5
)

When you have comprehensive findings from all sub-agents, call ResearchComplete.
</Task>

<Scaling Rules>
- **Comparisons** → 1 sub-agent per item (e.g., "X vs Y" = 2 agents, each researches one)
- **Complex multi-faceted** → analyze and split into logical sub-topics
- **Simple focused** → 1 agent with comprehensive questions
- **Bias towards clarity**: Better to have clear sub-topics than vague delegation
</Scaling Rules>

<Hard Limits>
- Max 3 concurrent sub-agents per iteration
- Max 6 total tool calls (think_tool + ConductResearch combined)
- MUST use think_tool BEFORE delegating and AFTER receiving findings
</Hard Limits>

**Critical Instructions**:
1. Use think_tool to PLAN your delegation strategy before calling ConductResearch
2. Generate SPECIFIC, ACTIONABLE questions for each sub-agent
3. After sub-agents return, use think_tool to ASSESS if you need more research
4. Each sub-agent should have DISTINCT, NON-OVERLAPPING subtopics
```

---

### **Phase 3: Integration Layer** 🟠 (MEDIUM PRIORITY)

**File**: `my_implementation/deep_research_agent.py`

#### Main Graph State (YOUR DESIGN)

```python
# File: my_implementation/shared/state.py

from typing_extensions import Annotated
from langgraph.graph import MessagesState
import operator

class FullResearchState(MessagesState):
    """Top-level state for entire research system.
    
    Shared keys are automatically passed to/from subgraphs by name matching.
    """
    
    # ===== From Advisor (advisor outputs these) =====
    research_topic: str = ""   # SHARED with supervisor
    research_scope: str = ""   # SHARED with supervisor
    user_approved: bool = False  # Private to main graph
    
    # ===== From Supervisor (supervisor outputs these) =====
    notes: Annotated[list[str], operator.add] = []      # SHARED with supervisor
    raw_notes: Annotated[list[str], operator.add] = []  # SHARED with supervisor
    
    # ===== From Writer (writer outputs this) =====
    final_report: str = ""  # Private to main graph
```

**Shared keys** (automatically passed by LangGraph):
- ✅ `research_topic`: Main graph ↔ Supervisor (string)
- ✅ `research_scope`: Main graph ↔ Supervisor (string)
- ✅ `notes`: Main graph ↔ Supervisor (list with `operator.add` reducer)
- ✅ `raw_notes`: Main graph ↔ Supervisor (list with `operator.add` reducer)

**Private keys** (NOT shared):
- `messages`: Main graph only (conversation history)
- `user_approved`: Main graph only (routing flag)
- `final_report`: Main graph only (final output)

#### Nodes

**Advisor** (already built - added as subgraph):
```python
# Your existing graph
# Returns: research_topic, research_scope, user_approved
```

**Supervisor** (added as subgraph):
```python
# The supervisor_agent you'll build in Phase 2
# Receives: research_topic, research_scope, notes[], raw_notes[]
# Returns: notes (filled with findings), raw_notes (filled)
```

**Report Writer** (simple node):
```python
async def write_final_report(state: FullResearchState):
    """Generate final report from supervisor's findings."""
    
    writer_model = init_chat_model(model="openai:gpt-4.1", max_tokens=32000)
    
    findings = "\n\n".join(state["notes"])
    
    prompt = f"""Write a comprehensive research report:

**Research Topic**: {state['research_topic']}

**Research Scope**: {state['research_scope']}

**Research Findings**:
{findings}

Create a well-structured report with:
- Title and introduction
- Main sections with headings (##)
- Specific facts and analysis
- Proper citations [Source Title](URL)
- Sources section at end

Be comprehensive and address all aspects of the research scope.
"""
    
    response = await writer_model.ainvoke([HumanMessage(content=prompt)])
    
    return {
        "final_report": response.content,
        "messages": [AIMessage(content=f"Here is your research report:\n\n{response.content}")]
    }
```

#### Graph Construction

```python
# File: my_implementation/deep_research_agent.py

from typing_extensions import Literal
from langgraph.graph import StateGraph, START, END

# Import subgraphs and components
from my_implementation.advisor.advisor_agent import graph as advisor_graph
from my_implementation.research_supervisor.research_supervisor_agent import supervisor_agent
from my_implementation.report_writer.report_writer import write_final_report
from my_implementation.shared.state import FullResearchState

# Build main graph
full_builder = StateGraph(FullResearchState)

# Add subgraphs and nodes
full_builder.add_node("advisor", advisor_graph)  # Level 1 → Level 2 (advisor subgraph)
full_builder.add_node("supervisor", supervisor_agent)  # Level 2 → Level 3 (supervisor subgraph)
full_builder.add_node("write_report", write_final_report)  # Simple node

# Routing logic
def route_after_advisor(state: FullResearchState) -> Literal["supervisor", END]:
    """Proceed to research supervisor if user approved, otherwise end."""
    if state.get("user_approved"):
        return "supervisor"
    return END

# Connect nodes
full_builder.add_edge(START, "advisor")
full_builder.add_conditional_edges("advisor", route_after_advisor)
full_builder.add_edge("supervisor", "write_report")
full_builder.add_edge("write_report", END)

# Compile main graph
deep_research_agent = full_builder.compile()
```

---

## 📊 STATE FLOW DIAGRAM

### Detailed State Handoffs

```
┌─────────────────────────────────────────────────────────────────┐
│ ADVISOR GRAPH                                                   │
│ Input: messages                                                 │
│ Output:                                                         │
│   - research_topic: "AI Impact on SWE Jobs"                     │
│   - research_scope: "Research hiring changes, skills..."       │
│   - user_approved: True                                         │
│   - messages: [conversation history]                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓ (if user_approved)
┌─────────────────────────────────────────────────────────────────┐
│ SUPERVISOR GRAPH                                                │
│ Input (from main graph, SHARED KEYS):                          │
│   - research_topic: "AI Impact on SWE Jobs"                     │
│   - research_scope: "Research hiring changes, skills..."       │
│   - notes: []                                                   │
│   - raw_notes: []                                              │
│                                                                │
│ Internal Process:                                              │
│ 1. supervisor analyzes scope                                   │
│ 2. Calls ConductResearch with:                                │
│    - research_subtopic: "AI impact on hiring"                 │
│    - research_questions: "How has AI changed..."              │
│    - max_searches: 5                                          │
│                                                                │
│ 3. supervisor_tools invokes sub-agent(s):                     │
│    ┌────────────────────────────────────┐                     │
│    │ RESEARCH AGENT 1                   │                     │
│    │ Input (NO parent context):         │                     │
│    │   - research_subtopic: "..."       │                     │
│    │   - research_questions: "..."      │                     │
│    │                                    │                     │
│    │ Output:                            │                     │
│    │   - compressed_research: "..."     │                     │
│    │   - raw_notes: [...]               │                     │
│    └────────────────────────────────────┘                     │
│                                                                │
│ 4. Accumulates findings in supervisor_messages                │
│                                                                │
│ Output (to main graph, SHARED KEYS):                          │
│   - notes: ["Sub-agent 1 findings", "Sub-agent 2 findings"]   │
│   - raw_notes: ["Raw 1", "Raw 2"]                             │
│   - research_topic: "AI Impact on SWE Jobs" (passed through)  │
│   - research_scope: "..." (passed through)                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ WRITE_REPORT NODE                                               │
│ Input:                                                         │
│   - research_topic: "AI Impact on SWE Jobs"                     │
│   - research_scope: "Research hiring changes..."               │
│   - notes: ["Finding 1", "Finding 2", ...]                    │
│                                                                │
│ Output:                                                         │
│   - final_report: "# AI Impact on SWE Jobs\n\n..."            │
│   - messages: [AIMessage with report]                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 UPDATED IMPLEMENTATION CHECKLIST

### ✅ Phase 0: Advisor (COMPLETE)
- [x] Built conversational advisor
- [x] Implemented search during scoping
- [x] Created execute_research tool trigger
- [x] Extracts research_topic and research_scope

---

### 🔴 Phase 1: Research Agent (3-4 hours)

**File organization**:
```
research_agent/
├── state.py              (ResearcherState)
├── research_agent.py     (Main graph)
├── prompts.py            (Agent prompts)
├── tools.py              (tavily_search)
└── __init__.py
```

**Order of implementation**:

- [ ] 1. Create directory structure:
  ```bash
  mkdir -p my_implementation/research_agent
  mkdir -p my_implementation/shared
  ```

- [ ] 2. Create `research_agent/state.py`:
  - Define `ResearcherState` with fields:
    - `researcher_messages: Annotated[Sequence[BaseMessage], add_messages]`
    - `research_subtopic: str` (from supervisor)
    - `research_questions: list[str]` (from supervisor - **LIST!**)
    - `compressed_research: str`
    - `raw_notes: Annotated[list[str], operator.add]`

- [ ] 3. Create `research_agent/prompts.py`:
  - `RESEARCH_AGENT_PROMPT` (generic, no subtopic/questions in it)
  - `COMPRESS_RESEARCH_PROMPT` (copy from course `prompts.py`)

- [ ] 4. Create `research_agent/tools.py`:
  - Implement `tavily_search` tool with webpage summarization

- [ ] 5. Create `shared/utils.py`:
  - Import/copy `think_tool` from course utils

- [ ] 6. Create `research_agent/research_agent.py`:
  - [ ] Implement `llm_call` node (system prompt does NOT include subtopic/questions)
  - [ ] Implement `tool_node` (collects raw_notes, handles think_tool)
  - [ ] Implement `compress_research` node (FINAL node after loop)
  - [ ] Implement `should_continue` routing function
  - [ ] Build graph with conditional routing
  - [ ] Compile: `researcher_agent = research_builder.compile()`

- [ ] 7. Test standalone:

```python
result = await researcher_agent.ainvoke({
    "researcher_messages": [HumanMessage("Subtopic: OpenAI\n\nQuestions: Features? Pricing?")],
    "research_subtopic": "OpenAI Deep Research",
    "research_questions": "What are the features? How does pricing work?"
})

assert result["compressed_research"]
assert len(result["raw_notes"]) >= 2  # At least 2 searches
```

**Acceptance criteria**:
- Uses think_tool after EACH search
- Stops after 5 searches OR when questions answered
- Compressed research is coherent
- Raw notes captured

---

### 🔴 Phase 2: Supervisor (4-5 hours) - MANDATORY

**File organization**:
```
research_supervisor/
├── state.py                          (SupervisorState)
├── research_supervisor_agent.py      (Main graph)
├── prompts.py                        (Supervisor prompt)
├── tools.py                          (ConductResearch, ResearchComplete)
├── utils.py                          (get_notes, format_instructions)
└── __init__.py
```

**Order of implementation**:

- [ ] 1. Create directory structure:
  ```bash
  mkdir -p my_implementation/research_supervisor
  ```

- [ ] 2. Create `research_supervisor/state.py`:
  - Define `SupervisorState` with YOUR fields:
    - `supervisor_messages: Annotated[Sequence[BaseMessage], add_messages]` (private)
    - `research_topic: str` (SHARED with main graph)
    - `research_scope: str` (SHARED with main graph)
    - `notes: Annotated[list[str], operator.add]` (SHARED)
    - `research_iterations: int` (private)
    - `raw_notes: Annotated[list[str], operator.add]` (SHARED)

- [ ] 3. Create `research_supervisor/tools.py`:
  - Define richer `ConductResearch` tool:
    - `research_subtopic: str`
    - `research_questions: list[str]` (**LIST!**)
    - `max_searches: int = 5`
  - Define `ResearchComplete` tool

- [ ] 4. Create `research_supervisor/utils.py`:
  - Implement `get_notes_from_tool_calls()` helper
  - Implement `format_research_instructions()` helper (formats list → numbered text)

- [ ] 5. Create `research_supervisor/prompts.py`:
  - Write YOUR supervisor prompt (shows example with list[str])

- [ ] 6. Create `research_supervisor/research_supervisor_agent.py`:
  - [ ] Implement `supervisor` node
  - [ ] Implement `supervisor_tools` node (with asyncio.gather)
  - [ ] Build supervisor graph
  - [ ] Compile: `supervisor_agent = supervisor_builder.compile()`

- [ ] 7. Test standalone:

```python
result = await supervisor_agent.ainvoke({
    "supervisor_messages": [HumanMessage("Compare OpenAI vs Gemini")],
    "research_topic": "Deep Research Comparison",
    "research_scope": "Compare OpenAI Deep Research to Gemini Deep Research",
    "notes": [],
    "raw_notes": []
})

assert len(result["notes"]) >= 2  # Multiple sub-agents
print(result["notes"])  # Should have separate findings
```

**Acceptance criteria**:
- Supervisor parallelizes comparisons (spawns 2+ sub-agents)
- Each sub-agent gets specific subtopic + questions
- Uses think_tool for strategy
- Returns within 6 iterations

---

### 🟠 Phase 3: Integration (2-3 hours)

**File organization**:
```
my_implementation/
├── deep_research_agent.py  (main graph - TOP LEVEL)
├── shared/
│   └── state.py            (FullResearchState)
└── report_writer/
    ├── report_writer.py    (write_final_report node)
    ├── prompts.py          (report template)
    └── __init__.py
```

**Order of implementation**:

- [ ] 1. Create directory structure:
  ```bash
  mkdir -p my_implementation/report_writer
  ```

- [ ] 2. Create `shared/state.py`:
  - Define `FullResearchState` (as shown in Phase 3 section above)
  - Mark SHARED vs. PRIVATE keys clearly

- [ ] 3. Create `report_writer/report_writer.py`:
  - Implement `write_final_report` node
  - Reads: `research_topic`, `research_scope`, `notes`
  - Returns: `final_report`, updates `messages`

- [ ] 4. Create `report_writer/prompts.py`:
  - Define report generation template

- [ ] 5. Create `deep_research_agent.py` (top-level):
  - Import advisor_graph, supervisor_agent, write_final_report
  - Build main graph with routing
  - Compile: `deep_research_agent = full_builder.compile()`

- [ ] 6. Test state passing:

```python
# After advisor:
state = {
    "research_topic": "...",
    "research_scope": "...",
    "user_approved": True
}

# Verify supervisor receives these shared keys
# Verify supervisor returns notes + passes through topic/scope
```

- [ ] 7. Test end-to-end:

```python
# Full conversation → research → report
result = full_agent.invoke({
    "messages": [HumanMessage("Research AI agents")]
}, config={"configurable": {"thread_id": "test-1", "recursion_limit": 50}})

assert "final_report" in result
assert state["research_topic"]  # Preserved through workflow
```

**Acceptance criteria**:
- Advisor completes successfully
- Supervisor receives both topic and scope
- Report includes all findings
- State properly passed through all levels

---

### 🟢 Phase 4: Prompts & Polish (1-2 hours)

- [ ] Create `report_prompts.py` with comprehensive report template
- [ ] Enhance RESEARCH_AGENT_PROMPT with better instructions
- [ ] Tune SUPERVISOR_PROMPT for better delegation
- [ ] Add citation formatting
- [ ] Test report quality

---

### 📊 Phase 5: Evaluation (3-4 hours)

**Component-level evals**:

- [ ] **Advisor eval**: 
  - Correctly extracts topic + scope
  - Proposes relevant directions
  - Converges in <5 turns

- [ ] **Research agent eval**:
  - Appropriate search depth (2-5 searches)
  - Uses think_tool consistently
  - Answers research questions

- [ ] **Supervisor eval**:
  - Correctly parallelizes comparisons
  - Generates good subtopics + questions
  - Stays within iteration limits

- [ ] **End-to-end eval**:
  - Report addresses scope
  - Citations present
  - Comprehensive coverage

---

## 🔑 CRITICAL IMPLEMENTATION NOTES

### **1. State Key Naming Consistency**

**IMPORTANT**: Your supervisor uses different field names than course:

| Graph Level | Field Name | Value | Notes |
|-------------|------------|-------|-------|
| **Main Graph** | `research_topic` | "AI Impact on SWE" | SHARED |
| **Main Graph** | `research_scope` | "Research hiring..." | SHARED |
| **Supervisor** | `research_topic` | "AI Impact on SWE" | SHARED (same key) |
| **Supervisor** | `research_scope` | "Research hiring..." | SHARED (same key) |
| **Research Agent** | `research_subtopic` | "AI hiring trends" | From supervisor |
| **Research Agent** | `research_questions` | "How has hiring changed?" | From supervisor |

**NOT USED**: `research_brief` (course uses this, you don't)

### **2. Tool Invocation Pattern**

**YOUR PATTERN** (richer schema):
```python
# Supervisor calls:
AIMessage(tool_calls=[{
    "name": "ConductResearch",
    "args": {
        "research_subtopic": "OpenAI Deep Research product",
        "research_questions": "What are the features? How does pricing work? User reviews?",
        "max_searches": 5
    },
    "id": "call_1"
}])

# supervisor_tools invokes:
researcher_agent.ainvoke({
    "research_subtopic": args["research_subtopic"],
    "research_questions": args["research_questions"],
    # Note: max_searches could be passed to configure agent behavior
})
```

### **3. Parallel Execution - asyncio.gather()**

**Pattern**:
```python
# Create coroutines (not executed yet):
coros = [
    researcher_agent.ainvoke({...})  # Coroutine 1
    for tc in conduct_research_calls
]

# Execute ALL in parallel:
tool_results = await asyncio.gather(*coros)
#                              ^ unpacking operator

# Result: List of state dictionaries from each sub-agent
```

### **4. Think Tool Placement**

**YOUR DECISION**: After EACH search

**Prompt enforcement**:
```
**CRITICAL**: After EVERY tavily_search, you MUST call think_tool to:
- Assess what you learned
- Identify information gaps
- Plan next search (if needed)
- Decide if you can answer research questions
```

**Message pattern**:
```
1. AIMessage(tool_calls=[tavily_search("query 1")])
2. ToolMessage(content="search results...")
3. AIMessage(tool_calls=[think_tool("I learned X, need Y...")])
4. ToolMessage(content="Reflection recorded")
5. AIMessage(tool_calls=[tavily_search("query 2")])
6. ... repeat ...
```

---

## 📁 FINAL FILE STRUCTURE (MODULAR ORGANIZATION)

```
my_implementation/
│
├── deep_research_agent.py              🟠 PHASE 3 - Top-level orchestration
│                                          (Main graph: advisor → supervisor → writer)
│
├── advisor/                            ✅ PHASE 0 - COMPLETE
│   ├── advisor_agent.py                   (Renamed from graph.py)
│   ├── prompts.py                         (Renamed from advisor_prompt.py)
│   ├── tools.py                           (Optional: search_web tool)
│   └── __init__.py
│
├── research_agent/                     🔴 PHASE 1 - Individual research agent
│   ├── research_agent.py                  (Main agent graph)
│   ├── prompts.py                         (RESEARCH_AGENT_PROMPT, COMPRESS_RESEARCH_PROMPT)
│   ├── tools.py                           (tavily_search with summarization)
│   ├── state.py                           (ResearcherState)
│   └── __init__.py
│
├── research_supervisor/                🔴 PHASE 2 - Multi-agent coordinator
│   ├── research_supervisor_agent.py       (Renamed from supervisor.py)
│   ├── prompts.py                         (SUPERVISOR_PROMPT)
│   ├── tools.py                           (ConductResearch, ResearchComplete)
│   ├── state.py                           (SupervisorState)
│   ├── utils.py                           (get_notes_from_tool_calls, format_research_instructions)
│   └── __init__.py
│
├── report_writer/                      🟢 PHASE 4 - Report generation
│   ├── report_writer.py                   (write_final_report node)
│   ├── prompts.py                         (Report generation template)
│   └── __init__.py
│
├── shared/                             🟢 PHASE 4 - Shared utilities
│   ├── state.py                           (FullResearchState - main graph state)
│   ├── utils.py                           (think_tool, common helpers)
│   └── __init__.py
│
├── tests/                              📊 PHASE 5 - Evaluations
│   ├── test_advisor.py
│   ├── test_research_agent.py
│   ├── test_supervisor.py
│   └── test_full_system.py
│
└── IMPLEMENTATION_ROADMAP.md           ✅ THIS FILE
```

**Import Pattern Example**:
```python
# In deep_research_agent.py:
from my_implementation.advisor.advisor_agent import advisor_graph
from my_implementation.research_supervisor.research_supervisor_agent import supervisor_agent
from my_implementation.report_writer.report_writer import write_final_report
from my_implementation.shared.state import FullResearchState
```

---

## 🎯 IMPLEMENTATION ORDER (RECOMMENDED)

### **Week 1: Core Components**

**Day 1-2**: Research Agent
- Build `research_agent.py` 
- Test with mock subtopic + questions
- Verify think_tool usage, compression

**Day 3-4**: Supervisor  
- Build `supervisor.py`
- Test delegation logic
- Verify parallel execution

**Day 5**: Integration
- Build `full_system.py`
- Connect advisor → supervisor → writer
- Test end-to-end

### **Week 2: Refinement**

**Day 1-2**: Prompts
- Refine all prompts based on testing
- Tune supervisor delegation strategy
- Enhance report formatting

**Day 3-5**: Evaluation
- Build eval datasets
- Test each component
- Measure quality metrics
- Iterate based on results

---

## 💻 CODE SNIPPETS FOR KEY PATTERNS

### **Pattern 1: Sub-Agent Invocation with YOUR Schema**

```python
# In supervisor_tools (research_supervisor/research_supervisor_agent.py):

from my_implementation.research_supervisor.utils import format_research_instructions

for tc in conduct_research_calls:
    # Extract supervisor-generated fields
    subtopic = tc["args"]["research_subtopic"]  # str
    questions = tc["args"]["research_questions"]  # list[str]
    max_searches = tc["args"].get("max_searches", 5)  # int
    
    # Format as HumanMessage (agent doesn't know it's a "subtopic")
    initial_message = format_research_instructions(subtopic, questions)
    # Result:
    # "Research the following topic:
    #  **Topic**: OpenAI Deep Research
    #  **Research Questions to Answer**:
    #  1. What are the key features?
    #  2. How does pricing work?
    #  3. What are user reviews?"
    
    # Invoke sub-agent with ISOLATED context
    result = await researcher_agent.ainvoke({
        "researcher_messages": [HumanMessage(content=initial_message)],
        "research_subtopic": subtopic,
        "research_questions": questions  # Store as list
    })
    
    # Extract findings
    compressed = result["compressed_research"]
    raw = result["raw_notes"]
```

### **Pattern 2: State Preservation in Supervisor**

```python
# At END of supervisor_tools:
if should_end:
    return Command(
        goto=END,
        update={
            # Extract findings
            "notes": get_notes_from_tool_calls(supervisor_messages),
            
            # MUST pass through shared keys (or they're lost):
            "research_topic": state["research_topic"],
            "research_scope": state["research_scope"],
            
            # raw_notes already accumulated via operator.add during loop
        }
    )
```

### **Pattern 3: Shared Keys Auto-Passing**

```python
# When you do:
full_builder.add_node("supervisor", supervisor_agent)

# LangGraph automatically:
# 1. Finds matching key names in both state schemas
# 2. Passes values from main → supervisor on invocation
# 3. Updates main state with supervisor's return values

# Shared keys (by name):
# - research_topic ✅
# - research_scope ✅
# - notes ✅
# - raw_notes ✅
```

---

## ⚠️ COMMON PITFALLS TO AVOID

### **Pitfall 1: Forgetting to Pass Through Shared Keys**

```python
# ❌ WRONG (in supervisor final return):
return Command(
    goto=END,
    update={"notes": [...]}  # Only notes, topic/scope LOST
)

# ✅ CORRECT:
return Command(
    goto=END,
    update={
        "notes": [...],
        "research_topic": state["research_topic"],  # Pass through
        "research_scope": state["research_scope"]   # Pass through
    }
)
```

### **Pitfall 2: Confusing Field Names**

```python
# ❌ WRONG:
supervisor_agent.ainvoke({
    "research_brief": state["research_scope"]  # supervisor doesn't have this field!
})

# ✅ CORRECT:
supervisor_agent.ainvoke({
    "research_topic": state["research_topic"],
    "research_scope": state["research_scope"]
})
```

### **Pitfall 3: Sub-Agent Gets Parent Context**

```python
# ❌ WRONG (context leakage):
researcher_agent.ainvoke({
    "research_topic": state["research_topic"],  # Parent topic!
    "research_scope": state["research_scope"]   # Parent scope!
})

# ✅ CORRECT (isolated context):
researcher_agent.ainvoke({
    "research_subtopic": tc["args"]["research_subtopic"],  # Specific assignment
    "research_questions": tc["args"]["research_questions"] # Specific questions
})
```

---

## 🧪 TESTING CHECKPOINTS

### **Checkpoint 1: After Research Agent**

Test that it works standalone:
```python
from my_implementation.research_agent.research_agent import researcher_agent

result = await researcher_agent.ainvoke({
    "researcher_messages": [HumanMessage(content="""
    Research the following topic:
    **Topic**: OpenAI Deep Research pricing
    
    **Research Questions to Answer**:
    1. What are the pricing tiers?
    2. What's included in each tier?
    3. How does it compare to competitors?
    """)],
    "research_subtopic": "OpenAI Deep Research pricing",
    "research_questions": [
        "What are the pricing tiers?",
        "What's included in each tier?",
        "How does it compare to competitors?"
    ]
})

# Verify:
assert "compressed_research" in result
assert "pricing" in result["compressed_research"].lower()
assert 2 <= len(result["raw_notes"]) <= 5  # 2-5 searches
```

### **Checkpoint 2: After Supervisor**

Test delegation:
```python
result = await supervisor_agent.ainvoke({
    "supervisor_messages": [HumanMessage("Compare OpenAI vs Gemini Deep Research")],
    "research_topic": "Deep Research Comparison",
    "research_scope": "Compare OpenAI Deep Research to Gemini Deep Research agents",
    "notes": [],
    "raw_notes": []
})

# Verify:
assert len(result["notes"]) >= 2  # At least 2 sub-agents
assert "OpenAI" in str(result["notes"])
assert "Gemini" in str(result["notes"])
```

### **Checkpoint 3: After Integration**

Test full flow:
```python
# Conversation with advisor:
result = full_agent.invoke({
    "messages": [HumanMessage("I want to research AI coding assistants")]
}, config=thread)

# Advisor proposes directions, user selects, confirms
result = full_agent.invoke({
    "messages": [HumanMessage("yes, proceed with the comparison")]
}, config=thread)

# Verify:
assert result["final_report"]
assert len(result["final_report"]) > 2000
assert "OpenAI" in result["final_report"]
```

---

## 🎓 RELEVANT COURSE MATERIALS

### Phase 1: Research Agent
- **Study**: `2_research_agent.ipynb`
- **Copy from**: `src/deep_research_from_scratch/research_agent.py`
- **Adapt**: Change state schema to use `research_subtopic` + `research_questions`

### Phase 2: Supervisor
- **Study**: `4_research_supervisor.ipynb`, `TECHNICAL_GUIDE_PART5_MULTI_AGENT.md`
- **Copy from**: `src/deep_research_from_scratch/multi_agent_supervisor.py`
- **Adapt**: Change state schema, tool schema (richer ConductResearch)

### Phase 3: Integration
- **Study**: `5_full_agent.ipynb`
- **Copy from**: `src/deep_research_from_scratch/research_agent_full.py`
- **Adapt**: Use your advisor graph, pass topic + scope (not brief)

---

## 📖 NEXT IMMEDIATE ACTION

**START HERE**: Create Phase 1 - Research Agent

```bash
cd my_implementation
mkdir -p research_agent
mkdir -p shared
touch research_agent/research_agent.py
touch research_agent/state.py
touch research_agent/prompts.py
touch research_agent/tools.py
touch research_agent/__init__.py
touch shared/utils.py
touch shared/state.py
```

**Begin with state definition** (`research_agent/state.py`):

```python
"""State schema for individual research agent."""

from typing_extensions import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
import operator

class ResearcherState(TypedDict):
    """State for individual research agent (Level 3).
    
    ISOLATED CONTEXT: No awareness of parent research or other agents.
    """
    researcher_messages: Annotated[Sequence[BaseMessage], add_messages]
    research_subtopic: str
    research_questions: list[str]  # ← LIST of questions
    compressed_research: str
    raw_notes: Annotated[list[str], operator.add]
```

**Then build main graph** (`research_agent/research_agent.py`):

```python
"""Individual research agent graph."""

from typing_extensions import Literal
from langgraph.graph import StateGraph, START, END

from my_implementation.research_agent.state import ResearcherState
# TODO: Import tools, prompts

# TODO: Define nodes (llm_call, tool_node, compress_research)
# TODO: Build graph
# TODO: Test

researcher_agent = ...  # Compiled graph
```

**Then follow Phase 1 checklist above!**

---

## 🚀 Summary: Your Custom Path

```
✅ Advisor (done) → 🔴 Research Agent → 🔴 Supervisor → 🟠 Integration → 🟢 Report Polish → 📊 Evaluation
```

**Estimated timeline**: 2-3 weeks for complete system with evaluations

---

## 🎨 YOUR UNIQUE ARCHITECTURAL INNOVATIONS

### **1. Modular File Structure**
```
my_implementation/
├── deep_research_agent.py  (orchestrator)
├── advisor/                (scoping module)
├── research_agent/         (execution module)
├── research_supervisor/    (coordination module)
├── report_writer/          (synthesis module)
└── shared/                 (common utilities)
```
**vs. Course**: Flat structure with all files in `src/deep_research_from_scratch/`

**Benefits**:
- ✅ Clear separation of concerns
- ✅ Easier to test modules independently
- ✅ Better for team collaboration
- ✅ Cleaner imports

---

### **2. Structured Research Questions** (`list[str]` vs. `str`)

**Course approach**:
```python
research_topic: str  # Single string with everything
```

**Your approach**:
```python
research_subtopic: str          # Focus area
research_questions: list[str]   # Structured list
```

**Benefits**:
- ✅ Better structured data (easier to validate, parse, display)
- ✅ LLM can generate clear, distinct questions
- ✅ Can count/track questions answered
- ✅ Formatted as numbered list in agent instructions

**Example**:
```python
# Supervisor generates:
{
    "research_subtopic": "OpenAI pricing",
    "research_questions": [
        "What are the pricing tiers?",
        "What features are in each tier?",
        "How does it compare to Gemini?"
    ]
}

# Formatted for agent:
"""
Research the following topic:
**Topic**: OpenAI pricing

**Research Questions to Answer**:
1. What are the pricing tiers?
2. What features are in each tier?
3. How does it compare to Gemini?
"""
```

---

### **3. Context Isolation via HumanMessage** (not system prompt)

**Course approach**:
```python
# Subtopic in system prompt
system_message = prompt.format(research_topic=subtopic)
```

**Your approach**:
```python
# System prompt is generic (no subtopic)
# Subtopic/questions in INITIAL HumanMessage
researcher_messages = [HumanMessage(content="Research topic: X\nQuestions: 1,2,3")]
```

**Benefits**:
- ✅ Cleaner separation (system prompt = instructions, user message = task)
- ✅ Agent doesn't know it's a "sub"-topic (just sees "topic")
- ✅ More natural message flow
- ✅ Easier to test (can vary initial message without changing prompt)

---

### **4. Dual Fields: topic + scope** (vs. single brief)

**Course approach**:
```python
research_brief: str  # Single field with everything
```

**Your approach**:
```python
research_topic: str   # High-level subject
research_scope: str   # Detailed instructions
```

**Benefits**:
- ✅ Clear semantic separation
- ✅ Topic can be used for titles, headers, categorization
- ✅ Scope provides full context without redundancy
- ✅ Supervisor sees BOTH (can analyze topic separately from scope)

---

### **5. Always-Supervisor Architecture**

**Course approach**:
- Optional multi-agent (can skip if not needed)

**Your approach**:
- **Mandatory** supervisor (even for single topics)

**Benefits**:
- ✅ Consistent architecture (all research goes through same path)
- ✅ Supervisor can decide 1 vs. N agents dynamically
- ✅ Future-proof (easy to scale)

**Trade-offs**:
- ⚠️ Slight overhead for simple single-topic research
- ✅ But: Offset by better organization and flexibility

---

## 📖 NEXT FILE TO CREATE

**Start here**: `my_implementation/research_agent/state.py`

**Then**: `my_implementation/research_agent/research_agent.py`

**Estimated time to working research agent**: 3-4 hours

**Ready to start building? 🚀**
