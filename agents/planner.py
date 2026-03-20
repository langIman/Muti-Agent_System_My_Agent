from agents.base import BaseAgent, parse_json, agent_log, extract_user_request


class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Planner",
            system_prompt=(
                "你是任务规划专家。根据 context 和 memory_result 生成执行计划。\n\n"
                "## 规则\n"
                "1. 输出 JSON 数组: [{{\"step\": 1, \"action\": \"...\", \"tool\": \"...\", \"params\": {{...}}}}]\n"
                "2. 每步必须是可执行的原子操作。如果任务简单可以只有一步。\n"
                "3. **尽可能一次性生成完整的计划**：包含所有必要的步骤（如找路径 -> 读内容 -> 写入修改）。只在\u201c必须先拿到前序结果，由于参数完全未知而无法编写下一步\u201d的极端情况下，才允许只生成 1 步并等待结果。\n"
                "4. **澄清规则**：只有当用户的指令**完全无法理解或存在严重歧义导致无法开始任何行动**时，才使用 `reply_user` 向用户提问澄清。如果指令的意图是清晰的，即使缺少部分细节（如具体文件路径），你也应该先通过 `list_directory`、`find_file` 等工具自主探索和推断，而不是直接问用户。\n"
                "5. **纯对话/问候场景**：当用户只是打招呼、闲聊或提问（不需要执行任何工具操作）时，直接生成 1 步计划，使用 `reply_user` 工具回复即可。\n"
                "6. 对于复杂的修改文件任务，典型流程是: find_file 找路径 → read_file 读内容 → write_file 写入内容。\n"
                "7. 🏁**任务结束判定**🏁：如果你确认用户的原始指令已经**完全执行成功、没有任何遗漏**（比如文件已经真正被修改了），你**必须**生成1步计划，使用 `task_complete` 工具结束整个会话！\n\n"
                "## 可用工具\n"
                "- web_search: 搜索互联网（关键词要简洁，不要用 site: 限定符，那样容易搜不到结果）\n"
                "- execute_python: 执行 Python 代码（独立环境，无法访问其他步骤的变量）\n"
                "- read_file: 读取文件\n"
                "- write_file: 写入文件\n"
                "- list_directory: 列出目录（仅第一层）\n"
                "- find_file: 按文件名递归搜索（会搜索所有子目录）\n"
                "- api_call: 调用 HTTP API\n"
                "- reply_user: 用于向用户提问、澄清意图，或当任务根本无法进行时给用户解释。\n"
                "- task_complete: 当所有步骤都已完成、真正的文件已被修改或动作已执行完毕时调用，结束任务。\n\n"
                "## ⚠️ 工具间数据传递规则（极其重要，违反会导致任务失败）\n"
                "**严禁在 web_search 之后使用 execute_python 处理搜索结果！这会导致 NameError 崩溃！**\n"
                "**严禁在任何工具之后使用 execute_python 引用前面工具的返回值！每个 execute_python 都是独立沙箱！**\n"
                "正确的搜索+写入流程：web_search → write_file（Executor 会自动根据搜索结果构造文件内容）\n"
                "execute_python 仅用于独立计算（如数学运算），绝不用于处理其他步骤的输出\n\n"
                "## 🚨 绝对规则\n"
                "**每个计划的最后一步必须是 `reply_user` 或 `task_complete`**。没有例外。如果你的计划最后一步不是这两个工具之一，系统会陷入死循环。\n"
            ),
            use_messages=True,  # 需要通过 placeholder 传入定制的 messages
        )

    def __call__(self, state):
        context_str = str(state.get("context", {}))
        memory_str = state.get("memory_result", "无相关记忆")
        user_request = extract_user_request(state)

        agent_log("Planner", "任务规划中...", f"用户请求: {user_request[:200]}\n记忆: {memory_str[:200]}")

        # 构建干净的消息 — 只注入 Planner 真正需要的信息，不注入完整对话历史
        plan_messages = [
            ("user", f"用户请求: {user_request}\n\n[感知上下文]: {context_str}\n[相关记忆]: {memory_str}"),
        ]

        # 如果是 replan，注入前面步骤的执行结果
        prev_results = state.get("tool_results", [])
        if prev_results:
            parts = []
            for tr in prev_results:
                tool_name = tr.get("tool", "unknown")
                result_text = tr.get("result", tr.get("content", ""))
                if result_text:
                    parts.append(f"[步骤{tr['step']+1}][{tool_name}] 结果: {str(result_text)[:2000]}")
            if parts:
                plan_messages.append(("user", f"[前面步骤的执行结果]:\n" + "\n".join(parts) + "\n\n请根据以上结果重新规划后续步骤。"))
            else:
                plan_messages.append(("user", "请生成执行计划。"))
        else:
            plan_messages.append(("user", "请生成执行计划。"))

        result = self.chain.invoke({
            **state,
            "messages": plan_messages,
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

        return {"messages": [], "plan": plan, "current_step": 0, "replan_count": state.get("replan_count", 0) + 1}
