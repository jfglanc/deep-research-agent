# Deep Agents Implementation Guide

**Last Updated**: November 10, 2025  
**Purpose**: Step-by-step guide for replacing research_supervisor + research_agent with LangChain Deep Agents

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Implementation Decisions](#implementation-decisions)
3. [File Structure Changes](#file-structure-changes)
4. [Step-by-Step Implementation](#step-by-step-implementation)
5. [State Management](#state-management)
6. [Message Flow](#message-flow)
7. [Configuration](#configuration)
8. [Testing Strategy](#testing-strategy)

---

## Architecture Overview

### Current System
```
Advisor → [approved?] → Supervisor (custom nodes) → Research Agents (parallel) → Report Writer
                             ├── supervisor node
                             ├── supervisor_tools node
                             └── Spawns researcher_agent graphs
```

### New System (Deep Agents)
```
Advisor → [approved?] → Deep Agent Supervisor → Deep Agent Report Writer
                             └── Spawns research-agent subagents
```

### Key Changes

1. **Replace custom supervisor + researcher graphs** with Deep Agents
2. **Use virtual filesystem** (StateBackend) for context management
3. **Eliminate custom state schemas** for supervisor/researcher
4. **Use middleware** for todos, files, and subagent spawning

---

## Implementation Decisions

### Core Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **State Management** | Virtual filesystem in main graph state (`files` dict) | Files shared across supervisor → subagents → report writer via StateBackend |
| **Deep Agent Creation** | Module-level instances (created once at import) | Efficient, reusable, fixed system prompts with dynamic messages |
| **State Passing** | Selective fields only (messages, files, todos) | Clean separation, no unnecessary fields passed |
| **Delegation Control** | LLM-driven via prompts and task() tool | Flexible, adapts to specific research requests |
| **Subagent Returns** | Natural language summary + file paths | Minimal context transfer, details preserved in files |
| **Compression Strategy** | Save-as-you-go + synthesize from memory | Raw searches saved to files, synthesis uses message history |
| **File Organization** | Supervisor specifies subfolder in task instruction | Each subagent writes to unique directory, prevents conflicts |
| **Index Updates** | Incremental (after each subagent completes) | Real-time progress tracking, supervisor maintains comprehensive index |
| **Config Organization** | By agent type | Clear separation of concerns |
| **Prompts** | General system prompt + detailed initial message | Reusable agents, specific instructions per invocation |
| **Report Format** | Single comprehensive prose-heavy format | Deep, well-structured reports with natural flow |

### Tool Implementation Decisions

| Tool | Implementation Choice | Rationale |
|------|----------------------|-----------|
| **tavily_search** | Single query, formatted output, no summarization | Simple, researcher controls iteration, LLM can batch queries in parallel |
| **URL Deduplication** | Not included | Single-query tool eliminates need |
| **Webpage Summarization** | Not included | Tavily's content field is sufficient, saves LLM calls |
| **Raw Content** | Not included | Use snippets not full HTML, saves tokens |
| **Formatted Output** | Included | Clear source numbering, readable structure |

### Workflow Decisions

| Workflow Aspect | Choice | Details |
|-----------------|--------|---------|
| **Researcher Workflow** | Save-as-you-go, synthesize from memory | Save raw searches to files, synthesize from message history (don't re-read) |
| **Supervisor Returns** | Files + final message only | Report writer gets supervisor summary + full filesystem |
| **Report Writer Returns** | Report in final_report field + message | Both for API access and user display |
| **Supervisor Initial Message** | Instructional with clear task breakdown | Reinforces key workflow steps and constraints |
| **Report Writer Initial Message** | Context-rich with supervisor summary | Supervisor summary + files + scope |

### What We're NOT Using

- ❌ SummarizationMiddleware (file system already offloads context, not needed)
- ❌ think_tool (removed per requirement)
- ❌ Separate compression node (handled via prompt in final response)
- ❌ Environment-based config (keeping it simple, hardcoded values)
- ❌ Real filesystem backend (virtual StateBackend for now, can upgrade later)
- ❌ Multiple report formats (single comprehensive format only)
- ❌ Webpage content summarization in tool (Tavily's content is sufficient)
- ❌ Raw webpage content (use Tavily snippets, saves tokens)
- ❌ URL deduplication (single-query tool, not needed)

---

## File Structure Changes

### Files to DELETE
```
src/research_supervisor/          (entire folder)
├── research_supervisor_agent.py  (228 lines)
├── state.py                       (52 lines)
├── prompts.py                     (88 lines)
├── tools.py                       (47 lines)
├── utils.py                       (76 lines)
└── __init__.py                    (7 lines)

src/research_agent/                (entire folder)
├── research_agent.py              (172 lines)
├── state.py                       (54 lines)
├── prompts.py                     (183 lines)
├── tools.py                       (197 lines)
└── __init__.py                    (7 lines)
```
**Total Deletion**: ~1,111 lines of code

### Files to CREATE
```
src/config.py                      (NEW - ~100 lines)
src/main_graph.py                  (RENAME from deep_research_agent.py)
src/research_deep_agent/           (NEW FOLDER)
├── __init__.py                    (NEW - ~15 lines)
├── supervisor.py                  (NEW - ~80 lines)
├── researcher_subagent.py         (NEW - ~35 lines)
├── prompts.py                     (NEW - ~350 lines)
└── tools.py                       (NEW - ~30 lines)
```

### Files to MODIFY
```
src/state.py                       (MODIFY - change 2 fields)
src/report_writer/report_writer.py (REPLACE - ~100 lines)
src/report_writer/prompts.py       (MODIFY - simplify to single format)
```

**Net Code Reduction**: ~600 lines (from 1,111 to ~510)

---

## Step-by-Step Implementation

### STEP 1: Create Configuration File

**File**: `src/config.py`

**Purpose**: Centralize all model and limit configurations for the entire system

**Structure**:
```python
"""Configuration for Deep Research Agent system.

All models, limits, and behavioral parameters are defined here.
Organized by agent type for clarity.
"""

from langchain.chat_models import init_chat_model

# ===== ADVISOR CONFIGURATION =====
ADVISOR_CONFIG = {
    "model": "claude-sonnet-4-5-20250929",
    "temperature": 0.8
}

def get_advisor_model():
    """Get initialized advisor model."""
    return init_chat_model(
        model=ADVISOR_CONFIG["model"],
        temperature=ADVISOR_CONFIG["temperature"]
    )

# ===== RESEARCH SUPERVISOR CONFIGURATION =====
RESEARCH_SUPERVISOR_CONFIG = {
    "model": "claude-sonnet-4-5-20250929",
    "temperature": 0
}

def get_supervisor_model():
    """Get initialized supervisor model."""
    return init_chat_model(
        model=RESEARCH_SUPERVISOR_CONFIG["model"],
        temperature=RESEARCH_SUPERVISOR_CONFIG["temperature"]
    )

# ===== RESEARCH SUBAGENT CONFIGURATION =====
RESEARCH_SUBAGENT_CONFIG = {
    "model": "gpt-5-mini",
    "temperature": 0
}

def get_researcher_model():
    """Get initialized researcher model."""
    return init_chat_model(
        model=RESEARCH_SUBAGENT_CONFIG["model"],
        temperature=RESEARCH_SUBAGENT_CONFIG["temperature"]
    )

# ===== REPORT WRITER CONFIGURATION =====
REPORT_WRITER_CONFIG = {
    "model": "claude-sonnet-4-5-20250929",
    "temperature": 0,
    "max_tokens": 32000
}

def get_report_writer_model():
    """Get initialized report writer model."""
    return init_chat_model(
        model=REPORT_WRITER_CONFIG["model"],
        temperature=REPORT_WRITER_CONFIG["temperature"],
        max_tokens=REPORT_WRITER_CONFIG["max_tokens"]
    )

# ===== RESEARCH BEHAVIORAL LIMITS =====
RESEARCH_LIMITS = {
    "max_subagents": 3,          # Max concurrent subagents supervisor can spawn
    "max_supervisor_iterations": 6,  # Max task() calls supervisor can make
    "max_researcher_searches": 5     # Max searches each researcher should perform
}

# ===== TAVILY SEARCH CONFIGURATION =====
TAVILY_CONFIG = {
    "max_results": 3,           # Results per search
    "topic": "general",         # general, news, or finance
    "include_raw_content": False  # Don't include full webpage HTML
}

# ===== FILE PATH CONSTANTS =====
RESEARCH_INDEX_PATH = "/research/index.md"
RESEARCH_BASE_DIR = "/research"
```

**Key Design Points**:
- Organized by agent type (clear separation)
- Helper functions to get initialized models
- Hardcoded values (no environment variables)
- Tavily configuration centralized
- File path constants for consistency

---

### STEP 2: Modify Main State

**File**: `src/state.py`

**Purpose**: Update state schema to support Deep Agents virtual filesystem

**Changes**:
```python
from typing_extensions import Annotated
from langgraph.graph import MessagesState

class FullResearchState(MessagesState):
    """Main graph state for Deep Research Agent.
    
    Supports Deep Agents virtual filesystem via 'files' and 'todos' fields.
    These are managed by Deep Agents middleware (FilesystemMiddleware, TodoListMiddleware).
    """
    
    # From advisor - research parameters
    research_topic: str = ""
    research_scope: str = ""
    user_approved: bool = False
    
    # Shared with deep agents (managed by middleware)
    files: dict[str, str] = {}  # Virtual filesystem: path → content
    todos: list[dict[str, str]] = []  # Todo tracking: [{"content": str, "status": str}]
    
    # Final output
    final_report: str = ""
```

**Removed Fields**:
- `notes: Annotated[list[str], operator.add]` - No longer needed (findings in files)
- `raw_notes: Annotated[list[str], operator.add]` - No longer needed (raw searches in files)

**Added Fields**:
- `files: dict[str, str]` - Virtual filesystem for all agents
- `todos: list[dict[str, str]]` - Todo tracking for planning

**No new imports needed** - MessagesState already provides everything required for Deep Agents compatibility.

---

### STEP 3: Create Research Deep Agent Module

#### File 3.1: `src/research_deep_agent/__init__.py`

**Purpose**: Export supervisor for use in main graph

```python
"""Research Deep Agent module using LangChain Deep Agents.

This module replaces the custom research_supervisor and research_agent
with LangChain's Deep Agents framework.
"""

from .supervisor import deep_research_supervisor

__all__ = ["deep_research_supervisor"]
```

**Note**: We only export the wrapper function, not internal components (subagent config, prompts, tools).
This keeps the interface clean - main graph only needs the supervisor function.

---

#### File 3.2: `src/research_deep_agent/tools.py`

**Purpose**: Define tavily_search tool for researchers

**Based on Documentation**: Deep Agents subagents receive tools as objects, not strings  
**Reference**: [Deep Agents Subagents Docs](https://docs.langchain.com/oss/python/deepagents/subagents)

**Implementation** (Simplified - 30 lines vs previous 197 lines):

```python
"""Research tools for Deep Agent researchers."""

from langchain_core.tools import tool
from tavily import TavilyClient

from src.config import TAVILY_CONFIG

# Initialize Tavily client
tavily_client = TavilyClient()


@tool
def tavily_search(query: str) -> str:
    """Search the web for information.
    
    Performs a single focused search query using Tavily API.
    Returns formatted results with source numbering for easy citation.
    
    Note: You can call this tool multiple times in parallel for different queries.
    Example: Search for "React learning curve" and "React hiring market" in the same turn.
    
    Args:
        query: A single search query to execute
    
    Returns:
        Formatted string with search results including titles, URLs, and content summaries
    """
    # Execute search using config
    results = tavily_client.search(
        query,
        max_results=TAVILY_CONFIG["max_results"],
        topic=TAVILY_CONFIG["topic"],
        include_raw_content=TAVILY_CONFIG["include_raw_content"]
    )
    
    # Format results with clear source numbering
    formatted = f"Search results for: {query}\n\n"
    
    for i, result in enumerate(results['results'], 1):
        formatted += f"--- SOURCE {i}: {result['title']} ---\n"
        formatted += f"URL: {result['url']}\n"
        formatted += f"CONTENT:\n{result['content']}\n"
        formatted += "-" * 80 + "\n\n"
    
    return formatted
```

**Design Decisions**:
- **Single query**: Researcher calls multiple times for depth (or batches in parallel)
- **No deduplication**: Not needed for single-query tool
- **No webpage summarization**: Tavily's content field is sufficient
- **No raw HTML**: Use snippets only, saves tokens
- **Formatted output**: Source numbering for easy citation
- **Config-driven**: max_results, topic, raw_content from config.py

---

#### File 3.3: `src/research_deep_agent/prompts.py`

**Purpose**: Define prompts for supervisor, researcher, and message templates

**Based on Documentation**: 
- [Deep Agents Customization](https://docs.langchain.com/oss/python/deepagents/customization)
- Course transcript: "Prompts are hundreds of lines for production agents"

**Structure** (~350 lines):

```python
"""Prompts for Research Deep Agent system."""

from src.shared.utils import get_today_str
from src.config import RESEARCH_LIMITS

# ===== SUPERVISOR SYSTEM PROMPT =====
# General, reusable prompt - no topic/scope (those go in message)

SUPERVISOR_SYSTEM_PROMPT = f"""You are a research supervisor coordinating specialized research subagents using LangChain Deep Agents framework.

Today's date: {get_today_str()}

<Your Role>
You coordinate comprehensive research by delegating to specialized subagents.
You do NOT conduct research yourself - you plan, delegate, and organize.

Your responsibilities:
1. Analyze research scope and identify distinct subtopics
2. Plan delegation strategy using todos
3. Spawn research subagents for each subtopic
4. Maintain a comprehensive research index
5. Ensure all aspects of scope are covered
</Your Role>

<Available Tools>
You have access to these tools through Deep Agents middleware:

1. **write_todos(todos: list[dict])** - Planning tool
   - Create todos before delegating: [{{"content": "Delegate X research", "status": "pending"}}]
   - Update todos as subagents complete: [{{"content": "...", "status": "completed"}}]
   - Use this to stay organized and track progress

2. **task(name: str, task: str)** - Subagent delegation tool
   - name: Always use "research-agent"
   - task: Clear instructions with subtopic, directory, and questions
   - Example: task(name="research-agent", task="Research React framework. Save findings to /research/react/ directory. Questions: 1) Learning curve? 2) Hiring market?")
   - You can spawn multiple subagents in parallel (max {RESEARCH_LIMITS['max_subagents']} concurrent)

3. **File System Tools** - Context management
   - ls(path): List files in directory
   - read_file(path): Read file contents
   - write_file(path, content): Create files
   - edit_file(path, old, new): Edit existing files

</Available Tools>

<Delegation Workflow>

STEP 1: PLAN YOUR APPROACH
- Read the research topic and scope from the user message
- Use write_todos to create your delegation plan
- Identify 2-4 distinct subtopics to research (depending on scope complexity)
- For each subtopic, formulate 2-4 specific research questions

STEP 2: SPAWN SUBAGENTS
- Use task() to delegate each subtopic to a research-agent
- Provide clear instructions including:
  * Specific subtopic focus
  * Directory to save findings: /research/[subtopic_slug]/
  * 2-4 specific research questions to answer
- You can spawn 2-3 subagents in parallel for efficiency
- Each subagent will conduct searches and create files in its directory

STEP 3: TRACK PROGRESS (AFTER EACH SUBAGENT RETURNS)
- When a subagent completes, it returns: "Research complete. Files created: /research/[slug]/findings.md..."
- Update your todos to mark that subtopic as complete
- Read the findings.md file (just to extract a 2-3 sentence summary)
- Update /research/index.md with the new entry (append to existing index)
- Continue until all subtopics researched

STEP 4: FINALIZE
- Ensure /research/index.md is complete with all subtopics
- Mark all todos as completed
- Provide comprehensive summary message including:
  * Total subtopics researched
  * Total sources collected (sum from all findings)
  * Brief highlights from each subtopic

</Delegation Workflow>

<Delegation Strategy Guidelines>

**For COMPARISONS** (e.g., "React vs Vue for startups"):
- Spawn 1 subagent per item being compared
- Example: 2 subagents for React vs Vue
- Directories: /research/react/ and /research/vue/
- Each researches independently

**For MULTI-FACETED TOPICS** (e.g., "AI impact on software engineering jobs"):
- Identify 2-4 logical dimensions
- Example dimensions: hiring trends, skill requirements, compensation changes, job roles evolution
- Spawn 1 subagent per dimension

**For SIMPLE TOPICS** (e.g., "What is LangChain?"):
- Spawn 1 subagent with comprehensive questions
- Directory: /research/langchain/

**CRITICAL**: Each subagent must have DISTINCT, NON-OVERLAPPING focus areas to avoid redundant research.

</Delegation Strategy Guidelines>

<File Organization>

Subagents will create files in this structure:
```
/research/
├── [subtopic_1]/
│   ├── findings.md         (Comprehensive findings with citations)
│   ├── sources.json        (All sources as JSON)
│   └── search_N_raw.md     (Raw search results, N = 1,2,3...)
├── [subtopic_2]/
│   ├── findings.md
│   ├── sources.json
│   └── search_N_raw.md
└── index.md                (YOU create and maintain this)
```

</File Organization>

<Index File Structure>

Create and maintain /research/index.md with this structure:

```markdown
# Research Index: [Research Topic]

## [Subtopic 1]
- Findings: /research/[slug1]/findings.md
- Sources: /research/[slug1]/sources.json  
- Source Count: [N] sources
- Summary: [2-3 sentence key findings extracted from findings.md]

## [Subtopic 2]
- Findings: /research/[slug2]/findings.md
- Sources: /research/[slug2]/sources.json
- Source Count: [N] sources
- Summary: [2-3 sentence key findings]

## Total Research Coverage
- [X] subtopics researched
- [Y] total sources collected
- Research completed: {get_today_str()}
```

Update this index AFTER EACH subagent completes (incremental updates).

</Index File Structure>

<Hard Constraints>
- Maximum {RESEARCH_LIMITS['max_subagents']} concurrent subagents per delegation batch
- Maximum {RESEARCH_LIMITS['max_supervisor_iterations']} total task() calls
- Always create /research/index.md before concluding
- Update index after each subagent completion (not just at the end)
- Do not read full findings files unless necessary (trust subagent summaries in their return messages)
</Hard Constraints>

<Critical Instructions>
1. **Plan before delegating**: Use write_todos to outline strategy
2. **Specify directories clearly**: Always tell subagents which directory to use
3. **Update index incrementally**: After each subagent returns, update the index
4. **Distinct subtopics**: Ensure no overlap between subagent assignments
5. **Final summary**: Provide comprehensive overview in your final message
</Critical Instructions>

Remember: You are the coordinator. Your subagents are the researchers. 
Stay organized, track progress, and maintain a clean research index.
"""

# ===== RESEARCHER SYSTEM PROMPT =====

RESEARCHER_SYSTEM_PROMPT = f"""You are a research agent conducting focused research on a specific subtopic.

Today's date: {get_today_str()}

<Your Task>
You will receive a research subtopic and specific questions to answer.
Your job is to:
1. Conduct web searches to gather comprehensive information
2. Save all findings to organized markdown files
3. Return a summary with file paths (NOT full content)
</Your Task>

<Available Tools>
- **tavily_search(query)**: Search the web for information
  * Returns formatted results with source numbering
  * You can call this multiple times in parallel for different queries
  * Example: Search "X learning curve" and "X hiring market" in the same turn

- **File System Tools**: Save your research
  * write_file(path, content): Create files
  * read_file(path): Read files (useful if you need to check what you've saved)
  * ls(path): List files in directory
</Available Tools>

<Research Workflow>

STEP 1: UNDERSTAND YOUR ASSIGNMENT
- Read the task carefully - what subtopic? What questions? What directory?
- Example task: "Research React framework. Save to /research/react/. Questions: 1) Learning curve? 2) Hiring market?"

STEP 2: CONDUCT SEARCHES
- Start with 1-2 broad searches covering the subtopic
- Follow with targeted searches for specific questions
- Save raw results after EACH search to /research/[subtopic]/search_N_raw.md
- Maximum {RESEARCH_LIMITS['max_researcher_searches']} searches

STEP 3: SYNTHESIZE FINDINGS
- Review all search results in your message history (don't re-read files)
- Write comprehensive findings.md file
- Write sources.json file with all sources

STEP 4: RETURN SUMMARY
- Provide brief summary with file paths
- Include key findings (2-3 sentences)
- State source count

</Research Workflow>

<File Organization>

You MUST create files in the directory specified in your task.

Required files:
1. **findings.md** - Comprehensive research findings
2. **sources.json** - All sources in JSON format  
3. **search_N_raw.md** - Raw search results (one file per search)

</File Organization>

<findings.md Structure - FLEXIBLE GUIDELINES>

Your findings.md file should include these sections (organize naturally):

1. **Title**: # [Subtopic Name]
2. **Research Questions**: ## Research Questions Addressed (numbered list)
3. **Findings**: ## Key Findings (organize with ### subsections as appropriate)
4. **Sources**: ## Sources (numbered list: [N] Title: URL)

**Guiding Principles**:
- Use clear markdown headings (##, ###) to organize content
- Include inline citations throughout findings [1], [2], [3]
- Preserve ALL relevant information verbatim (do not paraphrase important facts, quotes, statistics)
- Organize findings logically (by theme, by question, or by source - whatever flows best)
- Be comprehensive - include everything relevant to the research questions
- End with complete sources list in format: [1] Title: URL

**DO NOT** force artificial structure - organize in whatever way best presents your findings.

</findings.md Structure>

<sources.json Structure>

JSON array with source metadata:
```json
[
  {{
    "title": "Source Title",
    "url": "https://...",
    "relevance": "Brief note on why this source is relevant"
  }}
]
```

</sources.json Structure>

<search_N_raw.md Structure>

Save the FULL search results for traceability:
```markdown
# Search [N]: [query]

Date: {get_today_str()}

## Result 1: [Title]
URL: [url]
[Full content from Tavily]

## Result 2: [Title]
URL: [url]
[Full content]

... (all results)
```

Save these IMMEDIATELY after each search, before moving to next search.

</search_N_raw.md Structure>

<Final Response Format>

When research is complete, respond with this structure:

```
Research complete for [Subtopic].

Files created:
- /research/[slug]/findings.md (comprehensive findings)
- /research/[slug]/sources.json ([N] sources)
- /research/[slug]/search_1_raw.md through search_[M]_raw.md

Key findings: [2-3 sentence summary of most important discoveries]

Source count: [N] sources
```

**IMPORTANT**: Do NOT include the full content of files in your response.
Only provide file paths and brief summaries.

</Final Response Format>

<Hard Limits>
- Maximum {RESEARCH_LIMITS['max_researcher_searches']} tavily_search calls
- Must create findings.md and sources.json before finishing
- Save search results to search_N_raw.md after EACH search
- Stop when research questions are comprehensively answered OR max searches reached
</Hard Limits>

<Quality Standards>
- Comprehensive: Address all research questions thoroughly
- Well-cited: Include inline citations [1], [2] throughout findings
- Accurate: Preserve factual information verbatim from sources
- Organized: Use clear headings and logical flow
- Complete: Include all sources in both findings (inline) and sources list
</Quality Standards>

Remember: Your work will be read by a report writer who will synthesize findings
across multiple subtopics. Make your findings.md comprehensive and well-organized.
"""

# ===== MESSAGE TEMPLATES =====

SUPERVISOR_INITIAL_MESSAGE_TEMPLATE = """You are coordinating research on the following topic.

**Research Topic**: {research_topic}

**Research Scope**: {research_scope}

**Your Task**:
1. Analyze the research scope carefully to identify distinct subtopics that need investigation
2. Use write_todos to create your delegation plan (list out which subtopics to research)
3. Spawn specialized research subagents using task() - one subagent per distinct subtopic
4. For each subagent, provide:
   - Clear subtopic focus
   - Specific directory: /research/[subtopic_slug]/
   - 2-4 targeted research questions to answer
5. As each subagent completes, update /research/index.md with their findings summary
6. After all research is complete, provide a comprehensive summary

**Important Guidelines**:
- Spawn 2-3 subagents in parallel when possible (faster research)
- Ensure each subagent has DISTINCT, non-overlapping focus
- Update index.md incrementally (after each subagent, not just at the end)
- Your final message should summarize total research coverage

**Available Tools**: write_todos, task, ls, read_file, write_file, edit_file

Begin your research coordination now.
"""

REPORT_WRITER_INITIAL_MESSAGE_TEMPLATE = """Write a comprehensive research report on the following topic.

**Research Topic**: {research_topic}

**Research Scope**: {research_scope}

**Research Completed by Coordinator**:
{supervisor_summary}

**Your Task**:
1. Use file system tools to access research findings
2. Start by reading /research/index.md to understand what research was conducted
3. Read each subtopic's findings.md file for detailed information
4. Synthesize all findings into one cohesive, comprehensive report
5. Preserve all citations from the findings files
6. Ensure report addresses the research scope thoroughly

**Report Requirements**:
- Well-organized with clear markdown headings (##, ###)
- Prose-heavy (favor paragraphs over bullet points)
- Natural flow with logical organization
- Deep dive into findings (comprehensive, not superficial)
- All sources cited with inline references [1], [2] and final ## Sources section
- Professional tone, clear language

**Available Tools**: ls, read_file, write_file, write_todos

Read the research findings and synthesize your report now.
"""
```

**Key Design Points**:
- **Supervisor prompt**: Generic (no topic/scope), comprehensive instructions (~150 lines)
- **Researcher prompt**: Generic (no specific assignment), detailed guidelines (~180 lines)
- **Message templates**: Dynamic (include topic/scope), clear task instructions (~20 lines each)
- **No examples**: Guiding principles only, keeps prompts maintainable
- **Config-aware**: References limits from config.py
- **Incremental index updates**: Explicitly instructed in supervisor prompt

---

#### File 3.4: `src/research_deep_agent/researcher_subagent.py`

**Purpose**: Define research subagent configuration dict

**Based on Documentation**: [SubAgent Configuration](https://docs.langchain.com/oss/python/deepagents/subagents)

**Implementation**:

```python
"""Research subagent configuration for Deep Agents.

This subagent is spawned by the supervisor to conduct focused research
on specific subtopics. It has access to web search and file system tools.
"""

from .tools import tavily_search
from .prompts import RESEARCHER_SYSTEM_PROMPT
from src.config import RESEARCH_SUBAGENT_CONFIG

# Research subagent configuration
# Used by supervisor's SubAgentMiddleware to create research-agent instances
research_subagent = {
    "name": "research-agent",
    
    "description": (
        "Delegate focused research to this agent when you need comprehensive investigation "
        "of a specific subtopic with targeted research questions. "
        "\n\n"
        "Usage: Provide clear subtopic, directory path, and 2-4 specific questions. "
        "\n\n"
        "The agent will:\n"
        "- Conduct web searches to gather information\n"
        "- Save raw search results to files for traceability\n"
        "- Write comprehensive findings.md with citations\n"
        "- Create sources.json with all source metadata\n"
        "- Return summary with file paths (not full content)\n"
        "\n"
        "**Important**: Only delegate ONE subtopic per agent. For multiple subtopics, spawn multiple agents."
    ),
    
    "system_prompt": RESEARCHER_SYSTEM_PROMPT,
    
    "tools": [tavily_search],  # Only search tool, file tools provided by middleware
    
    "model": RESEARCH_SUBAGENT_CONFIG["model"]  # gpt-5-mini from config
}
```

**Design Points**:
- **Detailed description**: Helps supervisor understand when/how to use this subagent
- **Usage guidance**: Clarifies the interface (what to provide in task)
- **Expected outputs**: Clear about what files will be created
- **One subtopic rule**: Emphasized to prevent overloading single subagent
- **Model override**: Uses gpt-5-mini (cheaper than supervisor's claude-sonnet-4-5)

---

#### File 3.5: `src/research_deep_agent/supervisor.py`

**Purpose**: Create deep agent supervisor instance and wrapper function for main graph

**Based on Documentation**: 
- [create_deep_agent API](https://docs.langchain.com/oss/python/deepagents/overview)
- StateBackend is default backend (automatic)
- Middleware automatically attached (TodoListMiddleware, FilesystemMiddleware, SubAgentMiddleware)

**Implementation** (~80 lines):

```python
"""Deep Agent supervisor for research coordination.

This module creates the supervisor deep agent and provides a wrapper
function for integration with the main graph.
"""

from deepagents import create_deep_agent
from langchain_core.messages import HumanMessage

from src.state import FullResearchState
from src.config import RESEARCH_SUPERVISOR_CONFIG
from .researcher_subagent import research_subagent
from .prompts import SUPERVISOR_SYSTEM_PROMPT, SUPERVISOR_INITIAL_MESSAGE_TEMPLATE


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
```

**Key Design Decisions**:

1. **Module-Level Creation**: `supervisor_deep_agent` created once when module imports
   - More efficient (no recreation overhead)
   - System prompt is fixed (generic, reusable)
   - Topic/scope passed in message, not prompt

2. **Selective State Passing**: Only pass relevant fields
   - `messages`: Fresh message list (no advisor history)
   - `files`: Empty dict initially
   - `todos`: Empty list initially
   - Does NOT pass: `user_approved`, `final_report` (irrelevant to supervisor)

3. **Selective Return**: Only return what report writer needs
   - `files`: Complete filesystem with all research
   - `messages`: Just final summary message (not full supervisor conversation)
   - Pass through: `research_topic`, `research_scope` (required by report writer)
   - Does NOT return: `todos` (supervisor's internal planning, not needed after completion)

**What Report Writer Receives**:
```python
state = {
    "research_topic": "React vs Vue",
    "research_scope": "...",
    "files": {
        "/research/react/findings.md": "...",
        "/research/react/sources.json": "...",
        "/research/react/search_1_raw.md": "...",
        "/research/vue/findings.md": "...",
        "/research/vue/sources.json": "...",
        "/research/vue/search_1_raw.md": "...",
        "/research/index.md": "..."
    },
    "messages": [
        ...[advisor messages]...,
        AIMessage("Research complete. Index at /research/index.md. Covered: React (15 sources), Vue (12 sources)...")
    ]
}
```

---

### STEP 4: Modify Report Writer

**File**: `src/report_writer/report_writer.py`

**Purpose**: Replace with Deep Agent report writer

**Based on Documentation**: 
- [Deep Agents Customization](https://docs.langchain.com/oss/python/deepagents/customization)
- Report writer uses file system tools to read findings and synthesize report

**Implementation** (~100 lines):

```python
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
```

**Key Design Decisions**:

1. **Module-Level Creation**: Report writer created once (efficient)

2. **Single Report Format**: One comprehensive prompt (prose-heavy, well-structured)
   - No format detection needed
   - No multiple prompts to maintain
   - Report writer adapts structure to content naturally

3. **Return Strategy**: Report in both `final_report` field AND message
   - `final_report`: For programmatic access (API, downstream processing)
   - `messages`: For user display (shows report immediately)
   - If report is 20,000 tokens, message contains full report (user should see it)

4. **Input**: Receives supervisor's summary in message (provides context)

---

### STEP 5: Update Main Graph

**File**: `src/main_graph.py` (renamed from `deep_research_agent.py`)

**Purpose**: Wire Deep Agents into main graph, maintain same flow

**Changes**:

```python
"""Main graph for Deep Research Agent system.

Flow: Advisor → Supervisor (Deep Agent) → Report Writer (Deep Agent) → END
"""

from typing_extensions import Literal
from langgraph.graph import StateGraph, START, END

# State
from src.state import FullResearchState

# Agents
from src.advisor.advisor_agent import advisor_agent  # UNCHANGED
from src.research_deep_agent import deep_research_supervisor  # NEW (Deep Agent)
from src.report_writer.report_writer import write_final_report  # MODIFIED (Deep Agent)


# ===== ROUTING LOGIC =====

def route_after_advisor(state: FullResearchState) -> Literal["supervisor", "__end__"]:
    """Route to supervisor if approved, otherwise end."""
    if state.get("user_approved"):
        return "supervisor"
    return END


# ===== GRAPH CONSTRUCTION =====

full_builder = StateGraph(FullResearchState)

# Add nodes
full_builder.add_node("advisor", advisor_agent)
full_builder.add_node("supervisor", deep_research_supervisor)  # Deep Agent
full_builder.add_node("write_report", write_final_report)  # Deep Agent

# Add edges
full_builder.add_edge(START, "advisor")
full_builder.add_conditional_edges("advisor", route_after_advisor)
full_builder.add_edge("supervisor", "write_report")
full_builder.add_edge("write_report", END)

# Compile
deep_research_agent = full_builder.compile()
```

**Changes Made**:
1. **File renamed**: `deep_research_agent.py` → `main_graph.py` (clarity)
2. **Import updated**: `from src.research_deep_agent import deep_research_supervisor`
3. **Function name kept**: `write_final_report` (no rename needed, wrapper handles Deep Agent)
4. **No error handling**: Let failures propagate (can debug via LangSmith)
5. **Same graph structure**: No changes to flow, just implementation

**Graph Flow** (unchanged):
```
START → advisor → [approved?] → supervisor → write_report → END
                      ↓ No
                     END
```

---

## State Management

### Virtual Filesystem Flow

**Reference**: [Deep Agents StateBackend](https://docs.langchain.com/oss/python/deepagents/backends)

**Complete Flow with Incremental Index Updates**:

```
Initial State (after advisor):
{
    "files": {},
    "todos": [],
    "messages": [...],
    "research_topic": "React vs Vue for startups",
    "research_scope": "Compare for small team making tech decision"
}

↓ Supervisor wrapper creates message ↓

Supervisor receives:
{
    "messages": [HumanMessage("Research Topic: React vs Vue...")],
    "files": {},
    "todos": []
}

↓ Supervisor Turn 1: Planning ↓

Calls: write_todos([
    {"content": "Delegate React research", "status": "pending"},
    {"content": "Delegate Vue research", "status": "pending"},
    {"content": "Create comprehensive index", "status": "pending"}
])

↓ Supervisor Turn 2: Delegation ↓

Calls task() twice in parallel:
- task(name="research-agent", task="Research React. Save to /research/react/. Questions: 1) Learning curve? 2) Hiring?")
- task(name="research-agent", task="Research Vue. Save to /research/vue/. Questions: 1) Learning curve? 2) Hiring?")

↓ Subagent 1 (React) executes ↓

Turn 1: tavily_search("React learning curve 2025")
Turn 2: write_file("/research/react/search_1_raw.md", raw_results)
Turn 3: tavily_search("React hiring market startups")
Turn 4: write_file("/research/react/search_2_raw.md", raw_results)
Turn 5: write_file("/research/react/findings.md", synthesized_findings)
Turn 6: write_file("/research/react/sources.json", sources)
Turn 7: Returns "Research complete. Files: /research/react/findings.md (15 sources). Key findings: ..."

↓ Subagent 1 merges back to supervisor ↓

Supervisor now has:
files = {
    "/research/react/findings.md": "...",
    "/research/react/sources.json": "...",
    "/research/react/search_1_raw.md": "...",
    "/research/react/search_2_raw.md": "..."
}

↓ Supervisor Turn 3: Update after first subagent ↓

Calls: write_todos([...mark "Delegate React" as completed...])
Calls: read_file("/research/react/findings.md") to extract summary
Calls: write_file("/research/index.md", """
# Research Index: React vs Vue for Startups

## React for Startups
- Findings: /research/react/findings.md
- Sources: /research/react/sources.json
- Source Count: 15 sources
- Summary: React has moderate learning curve with strong hiring market...
""")

↓ Meanwhile, Subagent 2 (Vue) completes in parallel ↓

Returns with files = {"/research/vue/findings.md": "...", "/research/vue/sources.json": "...", ...}

↓ Framework merges Vue's files with supervisor's files ↓

Supervisor now has:
files = {
    "/research/react/findings.md": "...",
    "/research/react/sources.json": "...",
    "/research/react/search_1_raw.md": "...",
    "/research/react/search_2_raw.md": "...",
    "/research/vue/findings.md": "...",
    "/research/vue/sources.json": "...",
    "/research/vue/search_1_raw.md": "...",
    "/research/index.md": "[partial index with just React]"
}

↓ Supervisor Turn 4: Update after second subagent ↓

Calls: write_todos([...mark "Delegate Vue" as completed...])
Calls: read_file("/research/vue/findings.md") to extract summary
Calls: edit_file("/research/index.md", old_content, new_content_with_vue)
# OR write_file("/research/index.md", updated_full_index)  # Overwrites

↓ Supervisor Turn 5: Finalize ↓

Calls: write_todos([...mark "Create comprehensive index" as completed...])
Final message: "Research coordination complete. Index at /research/index.md. Covered: React (15 sources), Vue (12 sources). Total: 27 sources across 2 frameworks."

↓ Returns to main graph ↓

Main graph receives:
{
    "files": {[all files]},
    "messages": [AIMessage("Research coordination complete...")],
    "research_topic": "React vs Vue for startups",
    "research_scope": "..."
}
```

**Key Points**:
1. **Incremental index updates**: Supervisor updates index after EACH subagent completes
2. **Todos track progress**: Updated as subagents complete
3. **Files merge automatically**: Framework handles merging subagent files into supervisor files
4. **No read-back of raw searches**: Synthesis happens in subagent's message history
5. **Supervisor reads findings only**: Just to extract summary for index

---

## Message Flow Summary

### Complete System Message Flow

**Reference**: [Deep Agents Task Delegation](https://docs.langchain.com/oss/python/deepagents/harness)

```
=== ADVISOR PHASE ===
User: "I want to research React vs Vue for startups"
Advisor: [conversation to refine scope]
Advisor calls: execute_research(topic="React vs Vue", scope="Compare for small team...")
→ Sets user_approved = True

State passed to supervisor:
{
    "research_topic": "React vs Vue for startups",
    "research_scope": "Compare React and Vue for startup with small team making tech decision",
    "user_approved": True,
    "files": {},
    "todos": []
}

=== SUPERVISOR PHASE (DEEP AGENT) ===
Input: HumanMessage("[detailed task with topic and scope]")

Internal execution:
- Turn 1: write_todos (plan)
- Turn 2: task() × 2 (spawn React + Vue subagents in parallel)
- Turn 3: Update todos, read React findings, update index
- Turn 4: Update todos, read Vue findings, update index
- Turn 5: Final summary message

Output to main graph:
{
    "files": {[all 7+ files from both subagents + index]},
    "messages": [AIMessage("Research complete. Index at /research/index.md...")],
    "research_topic": "React vs Vue for startups",
    "research_scope": "..."
}

=== REPORT WRITER PHASE (DEEP AGENT) ===
Input: HumanMessage("[report task with supervisor summary]")

Internal execution:
- Turn 1: write_todos (plan sections)
- Turn 2: read_file("/research/index.md")
- Turn 3: read_file("/research/react/findings.md")
- Turn 4: read_file("/research/vue/findings.md")
- Turn 5: Synthesize report (in memory)
- Turn 6: Return full report in message

Output to main graph:
{
    "final_report": "[10,000 word comprehensive report]",
    "messages": [AIMessage("Here's your research report:\n\n[full report]")]
}

=== END ===
User receives comprehensive report
```

**Key Points**:
- Each Deep Agent sees only its relevant messages (clean context)
- Files persist and grow through the pipeline
- Only final messages propagate between phases
- Report writer gets supervisor's summary for context

---

## Technical Details & Edge Cases

### Config.py Prompt Integration

**Decision**: Config contains values only, prompts reference them via f-strings

```python
# Config values only
RESEARCH_LIMITS = {
    "max_subagents": 3,
    "max_iterations": 6,
    "max_researcher_searches": 5
}

# Prompts reference via f-string:
SUPERVISOR_PROMPT = f"""
...
Maximum {RESEARCH_LIMITS['max_subagents']} concurrent subagents
Maximum {RESEARCH_LIMITS['max_supervisor_iterations']} total task() calls
...
"""
```

This keeps config clean (just values) and prompts maintainable (references are explicit).

---

## Detailed Workflows

### Researcher Complete Workflow (Save-as-you-go + Synthesize from Memory)

**Decision**: Option C from Q45 - Save raw searches to files, synthesize from message history

**Step-by-Step Flow**:

```
Researcher receives from supervisor:
task(name="research-agent", task="Research React framework for startups. Save findings to /research/react/ directory. Questions: 1) What is the learning curve? 2) How is the hiring market? 3) What is the ecosystem like?")

Framework creates subagent state:
{
    "messages": [HumanMessage("Research React framework...")],
    "files": {},  # Empty or copied from supervisor
    "todos": []
}

↓ Researcher Executes ↓

TURN 1: First search
→ Calls: tavily_search("React learning curve for beginners 2025")
← Gets: ToolMessage("[3 search results, ~2KB]")
→ Calls: write_file("/research/react/search_1_raw.md", """
# Search 1: React learning curve for beginners 2025

## Result 1: React Official Docs
URL: https://react.dev/learn
CONTENT: [Tavily content]

## Result 2: React Tutorial 2025
URL: https://example.com
CONTENT: [Tavily content]

## Result 3: Learning React Survey
URL: https://example.com
CONTENT: [Tavily content]
""")
← Tool: "Created /research/react/search_1_raw.md"

TURN 2: Second search
→ Calls: tavily_search("React hiring market startups 2025")
← Gets: ToolMessage("[3 search results]")
→ Calls: write_file("/research/react/search_2_raw.md", "[formatted results]")
← Tool: "Created file"

TURN 3: Third search
→ Calls: tavily_search("React ecosystem Next.js tooling 2025")
← Gets: ToolMessage("[3 search results]")
→ Calls: write_file("/research/react/search_3_raw.md", "[formatted results]")
← Tool: "Created file"

[Researcher now has 3 ToolMessages with all search results in message history]
[AND has 3 raw search files saved]

TURN 4: Synthesize findings
→ LLM reviews its message history (sees all 3 ToolMessages)
→ Does NOT re-read search files (already has data in context)
→ Synthesizes comprehensive findings from message history
→ Calls: write_file("/research/react/findings.md", """
# React for Startups

## Research Questions Addressed
1. What is the learning curve?
2. How is the hiring market?
3. What is the ecosystem like?

## Key Findings

### Learning Curve and Developer Experience
React has a moderate learning curve. Developers with JavaScript experience can become productive in 2-3 weeks [1]. The introduction of Hooks in 2019 added initial complexity but improved code organization [2]...

[... comprehensive findings with inline citations ...]

## Sources
[1] React Official Documentation: https://react.dev/learn
[2] React Blog - Introducing Hooks: https://react.dev/blog/2019/02/06/react-v16.8.0
[3] Stack Overflow Survey 2024: https://stackoverflow.com/survey
...
[15] (15 total sources from 3 searches)
""")
← Tool: "Created findings.md"

TURN 5: Create sources JSON
→ Calls: write_file("/research/react/sources.json", """[
  {"title": "React Official Documentation", "url": "https://react.dev/learn", "relevance": "Primary source for learning resources"},
  {"title": "React Blog - Hooks", "url": "...", "relevance": "Historical context on Hooks introduction"},
  ...
]""")
← Tool: "Created sources.json"

TURN 6: Final response
→ LLM: "Research complete for React framework.

Files created:
- /research/react/findings.md (comprehensive findings with 15 citations)
- /research/react/sources.json (15 sources)
- /research/react/search_1_raw.md through search_3_raw.md (raw search data)

Key findings: React has a moderate learning curve but strong developer experience once mastered. Hiring market is robust with high demand in startup ecosystem. Mature ecosystem with Next.js providing full-stack capabilities.

Source count: 15 sources"

→ No more tool calls
← Subagent ends, returns to supervisor
```

**Critical Design Points**:

1. **Save raw searches immediately**: After each search, save to search_N_raw.md
   - **Purpose**: Traceability, can inspect later, preserves full source material
   - **NOT re-read**: Data already in message history for synthesis

2. **Synthesize from message history**: When ready, synthesize from ToolMessages in context
   - **Efficient**: No need to re-read files just saved
   - **Complete**: All search results are in message history
   - **Clean**: Uses existing context, no redundant file reads

3. **Files created**:
   - `search_N_raw.md`: Raw searches (saved as you go, NOT re-read)
   - `findings.md`: Synthesis (created from message history)
   - `sources.json`: Structured sources (created from message history)

4. **Return format**: Summary + file paths (not full content)

---

### Supervisor Index Management Workflow (Incremental Updates)

**Decision**: Incremental index updates after each subagent completes

**Detailed Flow**:

```
Supervisor Turn 1: Planning
→ Calls: write_todos([
    {"content": "Delegate React research", "status": "pending"},
    {"content": "Delegate Vue research", "status": "pending"},
    {"content": "Maintain research index", "status": "pending"}
])

Supervisor Turn 2: Spawn subagents in parallel
→ Calls: task(name="research-agent", task="Research React...")
→ Calls: task(name="research-agent", task="Research Vue...")

↓ Framework executes both subagents in parallel ↓

Subagent 1 (React) completes FIRST:
Returns: "Research complete. Files: /research/react/findings.md (15 sources)..."

↓ Supervisor Turn 3: Update after first completion ↓

Supervisor receives ToolMessage from React subagent
→ Calls: write_todos([...mark "Delegate React" as "completed"...])
→ Calls: read_file("/research/react/findings.md") 
← Gets: [full findings content]
→ Extracts 2-3 sentence summary from findings
→ Calls: write_file("/research/index.md", """
# Research Index: React vs Vue for Startups

## React for Startups
- Findings: /research/react/findings.md
- Sources: /research/react/sources.json
- Source Count: 15 sources
- Summary: React has moderate learning curve with strong hiring market. Mature ecosystem with Next.js.

## Research Status
- React: ✓ Completed
- Vue: In progress...
""")

Subagent 2 (Vue) completes NEXT:
Returns: "Research complete. Files: /research/vue/findings.md (12 sources)..."

↓ Supervisor Turn 4: Update after second completion ↓

Supervisor receives ToolMessage from Vue subagent
→ Calls: write_todos([...mark "Delegate Vue" as "completed"...])
→ Calls: read_file("/research/vue/findings.md")
← Gets: [full findings content]
→ Extracts summary
→ Calls: edit_file("/research/index.md", old_content, new_content)
# OR write_file (overwrites with updated index)

Updated index:
```markdown
# Research Index: React vs Vue for Startups

## React for Startups
- Findings: /research/react/findings.md
- Sources: /research/react/sources.json
- Source Count: 15 sources
- Summary: React has moderate learning curve with strong hiring market...

## Vue for Startups
- Findings: /research/vue/findings.md
- Sources: /research/vue/sources.json
- Source Count: 12 sources
- Summary: Vue has gentler learning curve, smaller but growing hiring market...

## Total Research Coverage
- 2 frameworks researched
- 27 total sources collected
- Research completed: {current_date}
```

↓ Supervisor Turn 5: Finalize ↓

→ Calls: write_todos([...mark "Maintain research index" as "completed"...])
→ Final message: "Research coordination complete. Index at /research/index.md. 
   Covered: React (15 sources), Vue (12 sources). Total: 27 sources across 2 frameworks.
   
   Key highlights:
   - React: Strong ecosystem, moderate learning curve
   - Vue: Gentle learning curve, growing market
   
   All findings available in /research/ directory."
```

**Why Incremental Updates**:
1. ✅ Real-time progress tracking
2. ✅ Index always reflects current state
3. ✅ Supervisor can monitor coverage as research progresses
4. ✅ If error occurs, partial results are captured
5. ✅ Allows supervisor to make adaptive decisions (spawn more subagents if gaps found)

**Implementation Note**: Use `write_file` to overwrite index (simpler than `edit_file`)

---

### Report Writer Complete Workflow

**Decision**: Write report directly in final message (Option A from Q47)

**Step-by-Step Flow**:

```
Report Writer receives from main graph:
{
    "messages": [
        ...[advisor messages]...,
        AIMessage("Research complete. Index at /research/index.md...")
    ],
    "research_topic": "React vs Vue for startups",
    "research_scope": "Compare for small team making tech decision",
    "files": {
        "/research/react/findings.md": "...",
        "/research/react/sources.json": "...",
        "/research/vue/findings.md": "...",
        "/research/vue/sources.json": "...",
        "/research/index.md": "..."
    }
}

↓ Report Writer wrapper creates message ↓

Initial message: "Write comprehensive report. Topic: React vs Vue. Scope: ... Research Summary: [supervisor's message]"

↓ Report Writer Deep Agent Executes ↓

TURN 1: Planning
→ Calls: write_todos([
    {"content": "Read research index", "status": "pending"},
    {"content": "Read React findings", "status": "pending"},
    {"content": "Read Vue findings", "status": "pending"},
    {"content": "Synthesize comprehensive report", "status": "pending"}
])

TURN 2: Read index
→ Calls: read_file("/research/index.md")
← Gets: [index content showing React and Vue with summaries]
→ Calls: write_todos([...mark "Read index" as completed...])

TURN 3: Read findings files
→ Calls: read_file("/research/react/findings.md")
← Gets: [comprehensive React findings with 15 citations]
→ Calls: read_file("/research/vue/findings.md")
← Gets: [comprehensive Vue findings with 12 citations]
→ Calls: write_todos([...mark reading tasks as completed...])

TURN 4: Generate report
→ LLM synthesizes report from findings in message history
→ Creates comprehensive markdown report:
   * Introduction
   * React section (from React findings)
   * Vue section (from Vue findings)
   * Comparative analysis (synthesizing both)
   * Conclusion
   * Sources (combined from both)
→ Calls: write_todos([...mark "Synthesize report" as completed...])
→ Returns final message with FULL REPORT CONTENT:

"# React vs Vue for Startups: A Comprehensive Comparison

## Introduction
[Context about the comparison, why it matters for startups]

## React for Startups

### Overview
[Synthesized from React findings]

### Learning Curve
[From React findings with citations [1], [2]]

### Hiring Market
[From React findings with citations [3], [4]]

### Ecosystem
[From React findings with citations [5], [6]]

## Vue for Startups

### Overview
[Synthesized from Vue findings]

### Learning Curve
[From Vue findings with citations [7], [8]]

... [continues for 5,000-10,000 words]

## Comparative Analysis

### Learning Curve Comparison
[Synthesizes React vs Vue findings]

### Hiring Market Comparison
[Synthesizes findings]

### Ecosystem Comparison
[Synthesizes findings]

### Decision Framework for Startups
[Practical guidance based on findings]

## Conclusion
[High-level synthesis and recommendations]

## Sources
[1] React Official Docs: https://react.dev
[2] React Hooks Introduction: https://...
... [all 27 sources combined and renumbered sequentially]
"

↓ Returns to main graph ↓

Report writer wrapper extracts report and returns:
{
    "final_report": "[full report content]",
    "messages": [AIMessage(content="Here's your research report:\n\n[full report]")]
}
```

**Key Points**:
1. **No file writes for report**: Report generated directly in final message
2. **Synthesis in memory**: LLM has all findings in context from read_file calls
3. **Comprehensive**: Report is long, detailed, prose-heavy (5,000-15,000 words)
4. **Single format**: Adapts structure naturally to content (comparison, topic, list - whatever fits)
5. **Citations preserved**: All sources from findings files included and renumbered
6. **Todos for planning**: Report writer uses todos to organize its work (optional but helpful)

---

### Report Writer Prompt Design

**Decision**: Single comprehensive format (not 3 separate formats)

**File**: `src/report_writer/prompts.py`

**Structure**:

```python
"""Prompts for Deep Agent report writer."""

from src.shared.utils import get_today_str

REPORT_WRITER_SYSTEM_PROMPT = f"""You are an expert research report writer.

Today's date: {get_today_str()}

<Your Role>
You synthesize research findings into comprehensive, well-written reports.
You read findings from files and create cohesive narratives that address the research scope.
</Your Role>

<Available Tools>
- ls(path): List files in directory
- read_file(path): Read file contents  
- write_file(path, content): Create files (optional)
- write_todos(todos): Plan report sections (optional)
</Available Tools>

<Report Writing Process>

STEP 1: DISCOVER RESEARCH
- Read /research/index.md to understand what was researched
- Identify all subtopic findings files

STEP 2: READ FINDINGS
- Read each subtopic's findings.md file
- Absorb all information, citations, and sources
- Note the relationships and themes across subtopics

STEP 3: SYNTHESIZE REPORT
- Create comprehensive narrative that addresses research scope
- Organize logically based on content (not forced structure)
- Preserve all important information from findings
- Combine and renumber citations sequentially

STEP 4: FINALIZE
- Ensure all sources are cited
- Verify report addresses original research scope
- Return complete report in your final message

</Report Writing Process>

<Report Quality Standards>

**Comprehensive and Deep**:
- Thoroughly address the research scope
- Include specific facts, statistics, and examples from findings
- Aim for 5,000-15,000 words depending on topic complexity
- Don't summarize superficially - dive deep into the material

**Well-Organized Structure**:
- Use clear markdown headings (##, ###)
- Logical flow that guides the reader
- Adapt structure to content:
  * For comparisons: Overview of each, then comparative analysis
  * For single topics: Overview, key dimensions, deep dives
  * For lists: Context, then detailed entries
- Natural organization (not forced templates)

**Prose-Heavy**:
- Favor paragraphs over bullet points
- Write in flowing, narrative style
- Connect ideas and themes across sections
- Professional but accessible tone

**Well-Cited**:
- Preserve all citations from findings files
- Use inline citations [1], [2] throughout
- Renumber sources sequentially (1, 2, 3, ... no gaps)
- End with ## Sources section listing all sources
- Format: [N] Source Title: URL

**Addresses Scope**:
- Ensure report directly addresses the research scope provided
- Connect findings back to original research questions
- Provide synthesis and insights, not just facts
- Include conclusions or recommendations where appropriate

</Report Quality Standards>

<Output Format>

Your final message should be the complete report in markdown format:

```markdown
# [Report Title Based on Topic]

## [First Major Section]
[Comprehensive prose with inline citations [1], [2]]

### [Subsection if needed]
[Detailed content with citations]

## [Second Major Section]
[Content...]

## [Additional Sections as appropriate]
[Content...]

## Conclusion
[Synthesis and final thoughts]

## Sources
[1] Source Title: URL
[2] Source Title: URL
...
[N] Last Source: URL
```

**DO NOT** write the report to a file - include it directly in your final message.
The report should be complete, comprehensive, and ready to present to the user.

</Output Format>

<Common Pitfalls to Avoid>
- Don't just concatenate findings - synthesize them
- Don't use bullet points excessively - write prose
- Don't lose citations - preserve all sources
- Don't ignore the research scope - address it directly
- Don't be superficial - go deep into the material
- Don't force artificial structure - let content guide organization
</Common Pitfalls to Avoid>

Remember: This is the final deliverable. Make it comprehensive, well-written, and valuable.
"""

# Message template included in research_deep_agent/prompts.py (shown earlier)
```

**Design Points**:
- **Single flexible format**: Report writer adapts structure to content naturally
- **Prose-heavy emphasis**: Favors paragraphs, natural flow
- **Quality over templates**: Guidelines not rigid structure
- **No format detection needed**: One great format for all research types
- **Comprehensive depth**: 5,000-15,000 word reports expected

---

## Implementation Checklist

### Phase 1: Foundation (Config & State)

**Files to create/modify**:
- [ ] Create `src/config.py` (~100 lines)
  - Model configurations for all agents
  - Research limits (max subagents, iterations, searches)
  - Tavily configuration
  - File path constants
  
- [ ] Modify `src/state.py` (2 field changes)
  - Remove: `notes`, `raw_notes`
  - Add: `files: dict[str, str]`, `todos: list[dict[str, str]]`
  - Add type hints for clarity

### Phase 2: Research Deep Agent Module

**Files to create**:
- [ ] Create `src/research_deep_agent/` folder
- [ ] Create `src/research_deep_agent/__init__.py` (~15 lines)
  - Export `deep_research_supervisor` function
  
- [ ] Create `src/research_deep_agent/tools.py` (~30 lines)
  - Simplified `tavily_search` tool
  - Single query, formatted output, no summarization
  
- [ ] Create `src/research_deep_agent/prompts.py` (~350 lines)
  - `SUPERVISOR_SYSTEM_PROMPT` (~150 lines)
  - `RESEARCHER_SYSTEM_PROMPT` (~180 lines)
  - `SUPERVISOR_INITIAL_MESSAGE_TEMPLATE` (~20 lines)
  
- [ ] Create `src/research_deep_agent/researcher_subagent.py` (~35 lines)
  - Subagent config dict with detailed description
  
- [ ] Create `src/research_deep_agent/supervisor.py` (~80 lines)
  - Module-level `create_deep_agent` instance
  - Wrapper function `deep_research_supervisor`
  - Selective state passing and return

### Phase 3: Report Writer

**Files to modify**:
- [ ] Replace `src/report_writer/report_writer.py` (~100 lines)
  - Module-level `create_deep_agent` instance
  - Wrapper function `write_final_report`
  - Extract supervisor summary from messages
  
- [ ] Modify `src/report_writer/prompts.py`
  - Single comprehensive format prompt
  - Message template with supervisor summary
  - Prose-heavy, flexible structure guidelines

### Phase 4: Main Graph

**Files to modify**:
- [ ] Rename `src/deep_research_agent.py` → `src/main_graph.py`
  - Update imports (new supervisor, new report writer)
  - Keep same graph structure
  - No error handling (let failures propagate)

### Phase 5: Cleanup

**Files to delete**:
- [ ] Delete `src/research_supervisor/` folder entirely (~500 lines)
- [ ] Delete `src/research_agent/` folder entirely (~600 lines)

**Total**: Delete ~1,111 lines, add ~510 lines = **600 line reduction**

---

## Key Reminders

### For Supervisor
- ✅ Updates index.md **incrementally** after each subagent
- ✅ Uses write_todos to track progress
- ✅ Specifies directory in each task() call
- ✅ Provides detailed initial message with task breakdown
- ✅ Returns only final message + files to main graph

### For Researcher
- ✅ Saves search_N_raw.md after EACH search
- ✅ Synthesizes from message history (doesn't re-read search files)
- ✅ Creates findings.md with flexible structure
- ✅ Returns summary + file paths (not full content)
- ✅ Single-query tavily_search, can batch in parallel

### For Report Writer
- ✅ Reads index.md first
- ✅ Reads all findings.md files
- ✅ Synthesizes in memory (doesn't write to file)
- ✅ Returns report in both final_report field and message
- ✅ Prose-heavy, comprehensive (5,000-15,000 words)

---

## Next Steps

Ready to implement! The complete specification is now documented.

**Recommended Build Order**:
1. `src/config.py` (foundation)
2. `src/state.py` (foundation)
3. `src/research_deep_agent/tools.py` (simple tool first)
4. `src/research_deep_agent/prompts.py` (comprehensive prompts)
5. `src/research_deep_agent/researcher_subagent.py` (wire prompts → config)
6. `src/research_deep_agent/supervisor.py` (wire everything → deep agent)
7. `src/research_deep_agent/__init__.py` (export)
8. `src/report_writer/prompts.py` (update prompts)
9. `src/report_writer/report_writer.py` (replace with deep agent)
10. `src/main_graph.py` (rename + update imports)
11. Delete old modules (cleanup)

**All design decisions documented. Ready to code.**

---

## Summary of Key Architectural Decisions

### State & Configuration
- ✅ Virtual filesystem via `state["files"]` dict (StateBackend)
- ✅ Centralized config.py organized by agent type
- ✅ Module-level deep agent creation (efficient, reusable)
- ✅ Selective state passing between agents (clean separation)
- ✅ Type hints for files and todos dicts

### Prompts & Messages
- ✅ General system prompts (no topic/scope)
- ✅ Topic/scope in detailed initial HumanMessage
- ✅ Instructional initial messages (clear task breakdown)
- ✅ No examples (guiding principles only)
- ✅ ~350 lines of prompts total (supervisor ~150, researcher ~180)

### Tools & Search
- ✅ Simplified tavily_search (~30 lines vs 197)
- ✅ Single query per call (can batch in parallel)
- ✅ Formatted output with source numbering
- ✅ No deduplication, summarization, or raw content
- ✅ Config-driven parameters

### Workflows
- ✅ **Researcher**: Save-as-you-go (search → save raw → search → save → synthesize from memory)
- ✅ **Supervisor**: Incremental index updates (after each subagent completes)
- ✅ **Report Writer**: Read files → synthesize → return in message

### Returns & Handoffs
- ✅ Supervisor returns: files + final message only
- ✅ Report writer returns: final_report field + message with report
- ✅ Subagents return: summary + file paths (not full content)

### Report Format
- ✅ Single comprehensive prose-heavy format
- ✅ Adapts structure naturally to content
- ✅ 5,000-15,000 word reports
- ✅ No format detection or multiple prompts

---

## Documentation References

- [Deep Agents Overview](https://docs.langchain.com/oss/python/deepagents/overview)
- [create_deep_agent API](https://docs.langchain.com/oss/python/deepagents/customization)
- [SubAgent Configuration](https://docs.langchain.com/oss/python/deepagents/subagents)
- [StateBackend](https://docs.langchain.com/oss/python/deepagents/backends)
- [Middleware Architecture](https://docs.langchain.com/oss/python/deepagents/middleware)
- [Task Delegation](https://docs.langchain.com/oss/python/deepagents/harness)

---

**Implementation Guide Complete** ✅  
**Total Decisions Made**: 50+  
**Ready to Build**: Yes  
**Next Step**: Begin implementation following checklist above
