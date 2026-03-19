import platform
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from agents.base import BaseAgent, agent_log


@tool
def get_system_info() -> dict:
    """获取系统环境信息"""
    return {"os": platform.system(), "python": platform.python_version()}

class PerceptionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Perceiver",
            system_prompt=(
                "你是环境感知专家。分析用户意图，提取关键信息。\n"
                "输出 JSON: {{\"intent\": \"...\", \"entities\": [...], \"needs_tools\": [...]}}"
            ),
        )
        self.tools = [get_system_info]
        self.tools_map = {t.name: t for t in self.tools}
        self.llm = self.llm.bind_tools(self.tools)
        self.chain = self.prompt | self.llm

    def __call__(self, state):
        agent_log("Perceiver", "环境感知中... 分析用户意图")

        result = self.chain.invoke(state)
        context = {"raw_response": result.content}

        agent_log("Perceiver", "感知结果", result.content or "(调用工具中...)")

        # 处理 tool_calls
        if result.tool_calls:
            msgs = [result]
            for tc in result.tool_calls:
                agent_log("Perceiver", f"调用工具: {tc['name']}", str(tc.get("args", {})))
                fn = self.tools_map.get(tc["name"])
                if fn:
                    output = fn.invoke(tc["args"])
                    msgs.append(ToolMessage(content=str(output), tool_call_id=tc["id"]))
                    context[tc["name"]] = output
                    agent_log("Perceiver", f"工具结果: {tc['name']}", str(output))
                else:
                    msgs.append(ToolMessage(content=f"未知工具: {tc['name']}", tool_call_id=tc["id"]))
            return {"messages": msgs, "context": context}

        return {"messages": [result], "context": context}
