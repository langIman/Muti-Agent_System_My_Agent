from orchestrator.core import build_graph


def main():
    graph = build_graph()

    print("Multi-Agent System 已启动 (输入 'quit' 退出)")
    while True:
        user_input = input("\n>>> ")
        if user_input.strip().lower() in ("quit", "exit"):
            break

        result = graph.invoke({
            "messages": [("user", user_input)],
            "context": {},
            "plan": [],
            "current_step": 0,
            "memory_query": "",
            "memory_result": "",
            "tool_results": [],
            "feedback1": {},
        })

        # 输出工具执行结果
        for tr in result.get("tool_results", []):
            if "result" in tr:
                print(f"\n[步骤{tr.get('step', '?')}] {tr.get('tool', '')}: {tr['result']}")
            elif tr.get("content"):
                print(f"\n[步骤{tr.get('step', '?')}]: {tr['content']}")
        # 输出最终回复
        final = result["messages"][-1]
        content = final.content if hasattr(final, "content") else str(final)
        if content:
            print(f"\n{content}")


if __name__ == "__main__":
    main()
