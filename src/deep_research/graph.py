### Research Advisor Agent ###

# this is a conversational agent with access to search to help you define the research direction
# it acts as a "research advisor" like a university professor would do
# if the topic is well known, it will use its own knowledge to define the direction
# but if it's a new or niche topic, it will use search to help you nail the scope using fresh context
# architecturally, it's a react agent with a tool to trigger the main deep research agent


### Imports ###

from typing_extensions import Literal, List

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode

from tavily.tavily import os
from tavily import TavilyClient

from src.deep_research.advisor_prompt import RESEARCH_ADVISOR_PROMPT, SEARCH_SUMMARIZER_PROMPT


## Clients and Models ##

model = ChatOpenAI(model="gpt-5-mini", temperature=0)
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))



## Graph State ##
# it inherits a list of messages + reducer from MessagesState
# it also includes three additional fields to store the direction of the research

class ResearchAdvisor(MessagesState):
    user_approved: bool
    research_topic: str
    research_scope: str




### Tools ###
# tavily accepts a list of queries and they get summarized with a research focus before returning to advisor
# execute_research acts as a structured output and trigger to the main deep research agent
# a node is added to save the output to the graph state

@tool(parse_docstring=True)
def search_web(queries: List[str], research_focus: str) -> str:
    """
    Tool to search the web for recent news and niche information based on the user's research focus.

    When to use:
    - When the user's research focus is a current event, recent news, or a niche topic
    - When the user's research focus is not well known or mainstream
    - When the user's research focus is not well defined or needs to be clarified
    
    Args:
        queries: A list of queries to search the web for.
        research_focus: The focus of the research based on your conversation with the user.

    Returns:
        A string summarizing the search results.
    """

    search_results = []
    for query in queries:
        # get 3 results for each query
        query_results = tavily_client.search(query, max_results=2)
        search_results.append(query_results)
    
    # summarize the results with a research focus
    system_message = SystemMessage(content=SEARCH_SUMMARIZER_PROMPT.format(research_focus=research_focus))
    results_to_summarize = HumanMessage(content=str(search_results))
    results_summary = model.invoke([system_message, results_to_summarize]).content
    
    # return the full summary
    return results_summary

@tool(parse_docstring=True)
def execute_research(research_topic: str, research_scope: str) -> str:
    """
    Tool to launch a long-running research task based on the user's research topic and scope.

    When to use:
    - When the user explicitly confirms a research direction and wants to proceed with a research task

    When NOT to use:
    - When the user is still exploring different research directions or needs more clarification
    
    Args:
        research_topic: The topic of the research.
        research_scope: The scope of the research.

    Returns:
        A string confirming that the research task has been launched.
    """
    return f"Research executed for {research_topic} with scope {research_scope}"



# we bind those two tools to the model
model_with_tools = model.bind_tools([search_web, execute_research])


### Nodes ###

# call_model and tool_node are the main ReAct nodes of the graph
def call_model(state: ResearchAdvisor) -> ResearchAdvisor:
    system_message = SystemMessage(content=RESEARCH_ADVISOR_PROMPT)
    messages = [system_message] + state["messages"]
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}

tool_node = ToolNode(tools=[search_web, execute_research])

# I created this extra node to save down the structured output of the execute_research tool to state
def save_research_brief(state: ResearchAdvisor) -> dict:
    
    # we need to look backwards to find the AI message with tool_calls
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

# these are the two routing functions for my conditional edges
# should_use_tools checks if the last message is an AI message with tool_calls
# route_after_tools checks if the last message is an AI message with tool_calls and the tool is execute_research

def should_use_tools(state: ResearchAdvisor) -> Literal["tool_node", "__end__"]:
    """Check if agent called tools and route to tool_node if true."""
    last_message = state["messages"][-1]
    
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tool_node"
    
    return END


def should_save_research_brief(state: ResearchAdvisor) -> Literal["save_research_brief", "continue"]:
    """Checks if execute_research tool was called and route to save_research_brief if true."""
    for message in reversed(state["messages"]):
        if isinstance(message, AIMessage) and message.tool_calls:
            tool_names = [tc["name"] for tc in message.tool_calls]
            if "execute_research" in tool_names:
                return "save_research_brief"
            return "continue"
    return "continue"



builder = StateGraph(ResearchAdvisor)

# add the three nodes to the graph
builder.add_node("call_model", call_model)
builder.add_node("tool_node", tool_node)
builder.add_node("save_research_brief", save_research_brief)

# add the edges to the graph
builder.add_edge(START, "call_model")

# if model calls tools, route to tool_node
builder.add_conditional_edges(
    "call_model",
    should_use_tools,
    {"tool_node": "tool_node", END: END}
)

# if execute_research tool is called, route to save_research_brief
builder.add_conditional_edges(
    "tool_node",
    should_save_research_brief,
    {
        "save_research_brief": "save_research_brief",
        "continue": "call_model"
    }
)

# once the research brief is saved, end the graph (no need to go back to the model)
builder.add_edge("save_research_brief", END)

# compile the graph
graph = builder.compile()


