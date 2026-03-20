import os
from datetime import datetime
from agents.base import BaseAgent, agent_log
from tools import ALL_TOOLS


class PerceptionAgent(BaseAgent):
    def __init__(self):
        # 构建静态环境上下文（替代原来的 get_system_info 工具）
        tool_names = [t.name for t in ALL_TOOLS]
        env_context = (
            f"当前工作目录: {os.getcwd()}\n"
            f"可用工具: {', '.join(tool_names)}"
        )

        super().__init__(
            name="Perceiver",
            system_prompt=(
                "你是环境感知专家。分析用户意图，提取关键信息。\n\n"
                f"## 环境信息\n{env_context}\n\n"
                "输出 JSON: {{\"intent\": \"...\", \"entities\": [...], \"needs_tools\": [...]}}"
            ),
            use_messages=True,  # Perception 需要读取对话历史来理解用户意图
        )
        # 不绑定任何工具 — Perception 是纯推理 Agent

    def __call__(self, state):
        agent_log("Perceiver", "环境感知中... 分析用户意图")

        # 注入当前时间（每次调用都不同，不适合写死在 system prompt）
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time_msg = ("system", f"当前时间: {current_time}")

        result = self.chain.invoke({
            **state,
            "messages": state["messages"] + [time_msg],
        })

        context = {"raw_response": result.content}
        agent_log("Perceiver", "感知结果", result.content)

        # 返回 AIMessage 到 messages（保持对话历史连贯）
        return {"messages": [result], "context": context}
