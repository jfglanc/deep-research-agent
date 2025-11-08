from langgraph.graph import StateGraph, START, END, add_messages, MessagesState
from tavily.tavily import os
from typing_extensions import TypedDict, Annotated, Sequence
from pydantic import BaseModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from tavily import TavilyClient

llm = ChatOpenAI(model="gpt-5-mini", temperature=0)

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

@tool
def search_tavily(query: str) -> str:
    """Search the web for information"""
    return "This is a search result"


class AgentInput(MessagesState):
    pass

class ResearchDirection(MessagesState):
    user_approved: bool
    research_topic: str
    research_parameters: str


