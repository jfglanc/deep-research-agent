### Research Advisor ###

from langgraph.graph import StateGraph, START, END, add_messages, MessagesState
from tavily.tavily import os
from typing_extensions import TypedDict, Annotated, Sequence
from pydantic import BaseModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from tavily import TavilyClient
from advisor_prompt import RESEARCH_ADVISOR_PROMPT
from langgraph.prebuilt import ToolNode


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
def propose_research(research_topic: str, research_scope: str) -> ResearchAdvisor:
    """Propose a research direction"""
    return ResearchAdvisor(user_approved=False, research_topic=research_topic, research_scope=research_scope)

@tool
def execute_research() -> ResearchAdvisor:
    """Execute a research brief"""
    return ResearchAdvisor(user_approved=True)



### Model ###

model = ChatOpenAI(model="gpt-5-mini", temperature=0)
model_with_tools = model.bind_tools([search_tavily])



### Nodes ###

def call_model(state: ResearchAdvisor) -> ResearchAdvisor:
    system_message = SystemMessage(content=RESEARCH_ADVISOR_PROMPT)
    messages = [system_message] + state.messages
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}

tool_node = ToolNode(tools=[search_tavily])

### Graph ###

builder = StateGraph(ResearchAdvisor)
builder.add_node("call_model", call_model)
builder.add_node("tool_node", tool_node)
builder.add_edge(START, "call_model")
builder.add_edge("call_model", "tool_node")
builder.add_edge("tool_node", END)
graph = builder.compile()


