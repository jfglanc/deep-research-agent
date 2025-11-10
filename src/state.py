from langgraph.graph import MessagesState


# ===== STATE FOR THE MAIN GRAPH =====

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