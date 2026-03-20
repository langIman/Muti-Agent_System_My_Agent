from agents.base import BaseAgent, agent_log
from tools import ALL_TOOLS


class ExecutorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Executor",
            system_prompt=(
                "你是执行专家。你必须通过调用工具来完成任务，不要用文字描述操作过程。\n\n"
                "## 核心规则\n"
                "1. 根据当前步骤的指令，选择**步骤中指定的工具**并调用，不要调用其他工具。\n"
                "2. 当步骤要求 write_file 时，你必须根据前面步骤的执行结果，自己构造完整的文件内容文本，作为 content 参数传给 write_file。\n"
                "3. 不要用占位符作为参数值，你必须填入真实内容。\n"
                "4. 如果前面步骤失败了或结果为空，你仍然应该尽力完成当前步骤（比如用你的知识补充内容）。\n"
            ),
        )

        self.tools = ALL_TOOLS
        self.tools_map = {t.name: t for t in self.tools}
        self.llm = self.llm.bind_tools(self.tools)
        self.chain = self.prompt | self.llm

    def __call__(self, state):
        plan = state.get("plan", [])
        idx = state.get("current_step", 0)
        if idx >= len(plan):
            agent_log("Executor", "⚠️ 无可执行步骤，跳过")
            return {
                "messages": [],
                "current_step": idx,
                "tool_results": state.get("tool_results", []) + [
                    {"step": idx, "tool": "reply_user", "result": "计划已执行完毕，无更多步骤。", "content": ""}
                ],
            }

        step = plan[idx]
        agent_log("Executor", f"执行步骤 {idx + 1}/{len(plan)}", str(step))

        # 构建干净的消息：用户原始输入 + 前面步骤的结果摘要 + 当前步骤指令
        # 不使用 state["messages"]，避免累积的 tool_calls 消息导致 API 格式校验失败
        exec_messages = []

        # 添加用户原始输入，让 Executor 知道最终目标
        orig_messages = state.get("messages", [])
        if orig_messages:
            first_msg = orig_messages[0]
            if isinstance(first_msg, tuple):
                exec_messages.append(("user", f"用户原始请求: {first_msg[1]}"))
            elif hasattr(first_msg, 'content'):
                exec_messages.append(("user", f"用户原始请求: {first_msg.content}"))

        # 添加前面步骤的工具结果摘要，让 LLM 知道之前做了什么
        prev_results = state.get("tool_results", [])
        if prev_results:
            summary_parts = []
            for tr in prev_results:
                tool_name = tr.get("tool", "unknown")
                result_text = tr.get("result", tr.get("content", ""))
                if result_text:
                    summary_parts.append(f"[步骤{tr['step']+1}][{tool_name}] 结果: {str(result_text)[:2000]}")
            if summary_parts:
                exec_messages.append(("user", "前面步骤的执行结果:\n" + "\n".join(summary_parts)))

        # 当前步骤指令
        exec_messages.append(("user", f"执行步骤: {step}"))

        result = self.chain.invoke({
            **state,
            "messages": exec_messages,
        })

        tool_output = {"step": state["current_step"], "content": result.content}

        # 处理 tool_calls
        if result.tool_calls:
            for tc in result.tool_calls:
                agent_log("Executor", f"调用工具: {tc['name']}", str(tc.get("args", {})))
                fn = self.tools_map.get(tc["name"])
                if fn:
                    out = fn.invoke(tc["args"])
                    tool_output["tool"] = tc["name"]
                    tool_output["result"] = str(out)
                    agent_log("Executor", f"工具返回: {tc['name']}", str(out)[:300])
                else:
                    error_msg = f"未知工具: {tc['name']}"
                    tool_output["error"] = error_msg
                    agent_log("Executor", f"⚠️ {error_msg}")
        else:
            if result.content:
                agent_log("Executor", "LLM 直接回复（未调用工具）", result.content[:300])

        return {
            "messages": [],
            "current_step": state["current_step"] + 1,
            "tool_results": state.get("tool_results", []) + [tool_output],
        }
