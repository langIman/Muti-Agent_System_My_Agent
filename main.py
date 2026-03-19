from orchestrator.core import build_graph, shared_short_term


def main():
    graph = build_graph()

    # 持久化的对话状态 — 跨轮次保留消息历史
    session_state = {
        "messages": [],
        "context": {},
        "plan": [],
        "current_step": 0,
        "memory_query": "",
        "memory_result": "",
        "short_term_context": "",
        "tool_results": [],
        "feedback": {},
    }

    print("Multi-Agent System 已启动 (输入 'quit' 退出)")
    while True:
        user_input = input("\n>>> ")
        if user_input.strip().lower() in ("quit", "exit"):
            break

        # 在现有消息历史基础上追加新的用户消息
        session_state["messages"].append(("user", user_input))
        # 重置本轮执行状态，但保留 messages 历史
        session_state["plan"] = []
        session_state["current_step"] = 0
        session_state["tool_results"] = []
        session_state["feedback"] = {}
        session_state["short_term_context"] = ""

        result = graph.invoke(session_state)

        # 更新持久状态：保留完整的消息历史
        session_state["messages"] = result["messages"]
        session_state["context"] = result.get("context", {})
        session_state["memory_result"] = result.get("memory_result", "")

        # 提取 AI 回复并写入短期记忆
        ai_reply = ""
        for tr in result.get("tool_results", []):
            if tr.get("tool") in ("reply_user", "task_complete"):
                ai_reply = tr["result"]
                print(f"\n💬 {ai_reply}")

        # 输出最终回复（跳过 Learner 的原始 JSON）
        final = result["messages"][-1]
        content = final.content if hasattr(final, "content") else str(final)
        if content and not content.strip().startswith("{"):
            if not ai_reply:
                ai_reply = content
            print(f"\n{content}")

        # 将本轮对话写入短期记忆
        shared_short_term.add(human=user_input, ai=ai_reply or "（无回复）")


if __name__ == "__main__":
    main()
