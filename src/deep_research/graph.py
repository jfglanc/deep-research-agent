from langgraph.graph import StateGraph, START, END, add_messages
from typing_extensions import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

def node_1(state: State) -> State:
    return {"messages": [HumanMessage(content="Hello, how are you?")]}

def node_2(state: State) -> State:
    return {"messages": [AIMessage(content="I'm doing great, thank you!")]}

builder = StateGraph(State)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
builder.add_edge("node_2", END)
graph = builder.compile()

