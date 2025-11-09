### Research Advisor ###

from typing_extensions import Literal

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode

from tavily.tavily import os
from tavily import TavilyClient

from src.deep_research.advisor_prompt import RESEARCH_ADVISOR_PROMPT



### State ###

class ResearchAdvisor(MessagesState):
    user_approved: bool
    research_topic: str
    research_scope: str

### Tools ###

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

@tool
def search_tavily(query: str) -> str:
    """Search the web for information"""
    return "This is a search result"

@tool
def execute_research(research_topic: str, research_scope: str) -> str:
    """Execute a research brief"""
    return f"Research executed for {research_topic} with scope {research_scope}"



### Model ###

model = ChatOpenAI(model="gpt-5-mini", temperature=0)
model_with_tools = model.bind_tools([search_tavily, execute_research])



### Nodes ###

def call_model(state: ResearchAdvisor) -> ResearchAdvisor:
    system_message = SystemMessage(content=RESEARCH_ADVISOR_PROMPT)
    messages = [system_message] + state.messages
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}

tool_node = ToolNode(tools=[search_tavily, execute_research])

def save_research_brief(state: ResearchAdvisor) -> ResearchAdvisor:
    last_message = state.messages[-1]
    for tool_call in last_message.tool_calls:
        if tool_call["name"] == "execute_research":
            args = tool_call["args"]
            research_topic = args["research_topic"]
            research_scope = args["research_scope"]
            return {
                "messages": [AIMessage(content=f"Executing research.")], 
                "user_approved": True,
                "research_topic": research_topic,
                "research_scope": research_scope
                }
    return state

### Graph ###

def route_after_tools(state: ResearchAdvisor) -> Literal["save_brief", "continue"]:
    for message in reversed(state["messages"]):
        if isinstance(message, AIMessage) and message.tool_calls:
            tool_names = [tool_call["name"] for tool_call in message.tool_calls]
            if "execute_research" in tool_names:
                return "save_brief"
            return "continue"
    return "continue"

builder = StateGraph(ResearchAdvisor)
builder.add_node("call_model", call_model)
builder.add_node("tool_node", tool_node)
builder.add_node("save_research_brief", save_research_brief)




builder.add_edge(START, "call_model")
builder.add_conditional_edges(
    "call_model",
    lambda state: "tool_node" if state["messages"][-1].tool_calls else END,
    {
        "tool_node": "tool_node",
        END: END
    }
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


