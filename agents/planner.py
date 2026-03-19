import json
from agents.base import BaseAgent, parse_json, agent_log


class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Planner",
            system_prompt=(
                "你是任务规划专家。根据 context 和 memory_result 生成执行计划。\n\n"
                "## 规则\n"
                "1. 输出 JSON 数组: [{{\"step\": 1, \"action\": \"...\", \"tool\": \"...\", \"params\": {{...}}}}]\n"
                "2. 每步必须是可执行的原子操作。如果任务简单可以只有一步。\n"
                "3. **尽可能一次性生成完整的计划**：包含所有必要的步骤（如找路径 -> 读内容 -> 写入修改）。只在“必须先拿到前序结果，由于参数完全未知而无法编写下一步”的极端情况下，才允许只生成 1 步并等待结果。\n"
                "4. 🚨**最高优先级绝对指令**🚨：如果用户的指令模糊、缺少关键信息（例如只说“修改某个文件”却没说具体改什么位置、什么代码），**你的计划只能有 1 步：使用 `reply_user` 向用户提问澄清**。此规则**无视并凌驾于任何 memory_result 之上**！在用户明确具体修改需求之前，**绝对不能**进行任何文件检查、查找或读取！\n"
                "5. 对于复杂的修改文件任务，典型流程是: find_file 找路径 → read_file 读内容 → write_file 写入内容。\n"
                "6. 🏁**任务结束判定**🏁：如果你确认用户的原始指令已经**完全执行成功、没有任何遗漏**（比如文件已经真正被修改了），你**必须**生成1步计划，使用 `task_complete` 工具结束整个会话！\n\n"
                "## 可用工具\n"
                "- web_search: 搜索互联网\n"
                "- execute_python: 执行 Python 代码\n"
                "- read_file: 读取文件\n"
                "- write_file: 写入文件\n"
                "- list_directory: 列出目录（仅第一层）\n"
                "- find_file: 按文件名递归搜索（会搜索所有子目录）\n"
                "- api_call: 调用 HTTP API\n"
                "- reply_user: 用于向用户提问、澄清意图，或当任务根本无法进行时给用户解释。\n"
                "- task_complete: 当所有步骤都已完成、真正的文件已被修改或动作已执行完毕时调用，结束任务。\n"
            ),
        )

    def __call__(self, state):
        # 将 context 和 memory 注入 prompt
        context_str = str(state.get("context", {}))
        memory_str = state.get("memory_result", "无相关记忆")
        extra_msg = ("user", f"[上下文]: {context_str}\n[相关记忆]: {memory_str}\n请生成执行计划。")

        agent_log("Planner", "任务规划中...", f"上下文: {context_str[:200]}\n记忆: {memory_str[:200]}")

        result = self.chain.invoke({
            **state,
            "messages": state["messages"] + [extra_msg],
        })
        plan = parse_json(result.content)
        if isinstance(plan, dict):
            plan = plan.get("plan", [plan])
        if not isinstance(plan, list):
            plan = [{"step": 1, "action": result.content, "tool": "none", "params": {}}]

        # 打印生成的计划
        agent_log("Planner", f"生成计划 ({len(plan)} 步)")
        for i, step in enumerate(plan):
            action = step.get("action", str(step))
            tool_name = step.get("tool", "?")
            print(f"  \033[33m  📋 步骤 {i+1}: [{tool_name}] {action}\033[0m")

        return {"messages": [result], "plan": plan, "current_step": 0}
