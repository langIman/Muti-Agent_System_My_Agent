from langchain_core.tools import tool

@tool
def task_complete(summary: str) -> str:
    """任务彻底完成时调用此工具以结束工作流。只有在你确信所有修改均已完成并核对无误时才能调用。"""
    return summary
