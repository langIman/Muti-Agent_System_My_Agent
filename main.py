from orchestrator.core import build_graph, shared_short_term
from learning.feedback import FeedbackCollector
from langchain_core.messages import HumanMessage
feedback_collector = FeedbackCollector()


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
        session_state["messages"].append(HumanMessage(content=user_input))

        # 重置本轮执行状态，但保留 messages 历史
        session_state["plan"] = []
        session_state["current_step"] = 0
        session_state["tool_results"] = []
        session_state["feedback"] = {}
        session_state["short_term_context"] = ""
        session_state["replan_count"] = 0

        result = graph.invoke(session_state)

        # 更新持久状态：保留完整的消息历史
        session_state["messages"] = result["messages"]
        session_state["context"] = result.get("context", {})
        session_state["memory_result"] = result.get("memory_result", "")

        # 提取 reply_user / task_complete 工具的回复并打印
        ai_reply = ""
        for tr in result.get("tool_results", []):
            if tr.get("tool") in ("reply_user", "task_complete"):
                ai_reply = tr["result"]
                print(f"\n💬 {ai_reply}")

        # 兜底：若工具未回复，尝试从最后一条消息提取（跳过 Learner 的原始 JSON）
        if not ai_reply:
            final = result["messages"][-1]
            content = final.content if hasattr(final, "content") else str(final)
            if content and not content.strip().startswith("{"):
                ai_reply = content
                print(f"\n{content}")

        # 收集系统反馈
        task_desc = result.get("context", {}).get("intent", user_input[:50])
        has_error = any(tr.get("error") for tr in result.get("tool_results", []))
        feedback_collector.collect_system_feedback(
            task=task_desc,
            success=not has_error,
            error=str([tr["error"] for tr in result.get("tool_results", []) if tr.get("error")]) if has_error else "",
        )

        # 将本轮对话写入短期记忆
        shared_short_term.add(human=user_input, ai=ai_reply or "（无回复）")


if __name__ == "__main__":
    main()
