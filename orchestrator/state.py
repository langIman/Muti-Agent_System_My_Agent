from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    context: dict
    plan: list[dict]
    current_step: int
    memory_query: str
    memory_result: str
    short_term_context: str   # 短期记忆：最近对话上下文
    tool_results: list
    feedback: dict
