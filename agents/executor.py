from langchain_core.messages import ToolMessage
from agents.base import BaseAgent, agent_log
from tools import ALL_TOOLS


class ExecutorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Executor",
            system_prompt="你是执行专家。你必须通过调用工具来完成任务，不要用文字描述操作过程。根据当前步骤的指令，选择合适的工具并调用。",
        )

        self.tools = ALL_TOOLS
        self.tools_map = {t.name: t for t in self.tools}
        self.llm = self.llm.bind_tools(self.tools)
        self.chain = self.prompt | self.llm

    def __call__(self, state):
        step = state["plan"][state["current_step"]]
        agent_log("Executor", f"执行步骤 {state['current_step'] + 1}/{len(state['plan'])}", str(step))

        result = self.chain.invoke({
            **state,
            "messages": state["messages"] + [("user", f"执行步骤: {step}")],
        })

        tool_output = {"step": state["current_step"], "content": result.content}
        msgs = [result]

        # 处理 tool_calls
        if result.tool_calls:
            for tc in result.tool_calls:
                agent_log("Executor", f"调用工具: {tc['name']}", str(tc.get("args", {})))
                fn = self.tools_map.get(tc["name"])
                if fn:
                    out = fn.invoke(tc["args"])
                    msgs.append(ToolMessage(content=str(out), tool_call_id=tc["id"]))
                    tool_output["tool"] = tc["name"]
                    tool_output["result"] = str(out)
                    agent_log("Executor", f"工具返回: {tc['name']}", str(out)[:300])
                else:
                    error_msg = f"未知工具: {tc['name']}"
                    tool_output["error"] = error_msg
                    msgs.append(ToolMessage(content=error_msg, tool_call_id=tc["id"]))
                    agent_log("Executor", f"⚠️ {error_msg}")
        else:
            if result.content:
                agent_log("Executor", "LLM 直接回复（未调用工具）", result.content[:300])

        return {
            "messages": msgs,
            "current_step": state["current_step"] + 1,
            "tool_results": state.get("tool_results", []) + [tool_output],
        }
