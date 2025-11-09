### Research Advisor ###

from typing_extensions import Literal, List

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode

from tavily.tavily import os
from tavily import TavilyClient

from src.deep_research.advisor_prompt import RESEARCH_ADVISOR_PROMPT, SEARCH_SUMMARIZER_PROMPT

model = ChatOpenAI(model="gpt-5-mini", temperature=0)
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

### State ###

class ResearchAdvisor(MessagesState):
    user_approved: bool
    research_topic: str
    research_scope: str

### Tools ###


summarizer_model = ChatOpenAI(model="gpt-5-mini", temperature=0)

@tool
def search_tavily(queries: List[str], research_focus: str) -> str:
    """Search the web for information"""

    search_results = []
    for query in queries:
        # get 3 results for each query
        query_results = tavily_client.search(query, max_results=2)
        search_results.append(query_results)
    
    # summarize the results with a research focus
    system_message = SystemMessage(content=SEARCH_SUMMARIZER_PROMPT.format(research_focus=research_focus))
    results_to_summarize = HumanMessage(content=str(search_results))
    results_summary = summarizer_model.invoke([system_message, results_to_summarize]).content
    
    # return the full summary
    return results_summary

@tool
def execute_research(research_topic: str, research_scope: str) -> str:
    """Execute a research brief"""
    return f"Research executed for {research_topic} with scope {research_scope}"



### Model ###


model_with_tools = model.bind_tools([search_tavily, execute_research])



### Nodes ###

def call_model(state: ResearchAdvisor) -> ResearchAdvisor:
    system_message = SystemMessage(content=RESEARCH_ADVISOR_PROMPT)
    messages = [system_message] + state["messages"]
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}

tool_node = ToolNode(tools=[search_tavily, execute_research])

def save_research_brief(state: ResearchAdvisor) -> dict:
    
    for message in reversed(state["messages"]):
        if isinstance(message, AIMessage) and message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call["name"] == "execute_research":
                    args = tool_call["args"]
                    return {
                        "user_approved": True,
                        "research_topic": args["research_topic"],
                        "research_scope": args["research_scope"]
                    }
    
    return {}

### Graph ###

def route_after_tools(state: ResearchAdvisor) -> Literal["save_research_brief", "continue"]:
    for message in reversed(state["messages"]):
        if isinstance(message, AIMessage) and message.tool_calls:
            tool_names = [tc["name"] for tc in message.tool_calls]
            if "execute_research" in tool_names:
                return "save_research_brief"
            return "continue"
    return "continue"

def should_use_tools(state: ResearchAdvisor) -> Literal["tool_node", "__end__"]:
    """Check if agent called tools."""
    last_message = state["messages"][-1]
    
    # Only AIMessage has tool_calls
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tool_node"
    
    return END

builder = StateGraph(ResearchAdvisor)
builder.add_node("call_model", call_model)
builder.add_node("tool_node", tool_node)
builder.add_node("save_research_brief", save_research_brief)




builder.add_edge(START, "call_model")


builder.add_conditional_edges(
    "call_model",
    should_use_tools,
    {"tool_node": "tool_node", END: END}
)
builder.add_conditional_edges(
    "tool_node",
    route_after_tools,
    {
        "save_research_brief": "save_research_brief",
        "continue": "call_model"
    }
)

builder.add_edge("save_research_brief", END)
graph = builder.compile()


