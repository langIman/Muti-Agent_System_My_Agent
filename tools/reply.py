from langchain_core.tools import tool


@tool
def reply_user(message: str) -> str:
    """回复用户消息。当需要向用户提供信息、回答问题、或请求澄清时使用此工具。"""
    return message
