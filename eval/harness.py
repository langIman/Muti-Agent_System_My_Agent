"""评估执行器：用 graph.stream() 零侵入地捕获每个 Agent 节点的输出。"""
import subprocess
from langchain_core.messages import HumanMessage
from orchestrator.core import build_graph, shared_short_term


class EvalHarness:
    def __init__(self, cases: list):
        self.cases = cases

    def run_case(self, case: dict, run_id: int = 0) -> dict:
        """运行单个测试用例，捕获每个节点的 state update。"""
        # 前置 setup（如创建临时文件）
        for cmd in case.get("setup", []):
            subprocess.run(cmd, shell=True, timeout=10)

        # 清理跨测试污染
        shared_short_term.clear()

        graph = build_graph()

        initial_state = {
            "messages": [HumanMessage(content=case["input"])],
            "context": {},
            "plan": [],
            "current_step": 0,
            "memory_query": "",
            "memory_result": "",
            "short_term_context": "",
            "tool_results": [],
            "feedback": {},
            "replan_count": 0,
        }

        # plan 和 execute 都可能被多次调用（replan），用列表收集
        node_outputs = {"execute": [], "plan": []}
        final_state = dict(initial_state)

        for event in graph.stream(initial_state):
            for node_name, update in event.items():
                if node_name in ("execute", "plan"):
                    node_outputs[node_name].append(update)
                else:
                    node_outputs[node_name] = update
                # 合并到 final_state
                for k, v in update.items():
                    if k == "messages":
                        final_state["messages"] = final_state.get("messages", []) + v
                    else:
                        final_state[k] = v

        # 后置 teardown
        for cmd in case.get("teardown", []):
            subprocess.run(cmd, shell=True, timeout=10)

        return {
            "case_id": case["id"],
            "run_id": run_id,
            "input": case["input"],
            "category": case.get("category", "unknown"),
            "node_outputs": node_outputs,
            "final_state": final_state,
        }

    def run_all(self, num_runs: int = 1, categories: list = None) -> list:
        """运行全部（或过滤后的）测试用例。"""
        cases = self.cases
        if categories:
            cases = [c for c in cases if c.get("category") in categories]

        results = []
        for case in cases:
            for run_id in range(num_runs):
                print(f"\n{'='*60}")
                print(f"Running: {case['id']} (run {run_id + 1})")
                print(f"{'='*60}")
                try:
                    result = self.run_case(case, run_id)
                    results.append(result)
                except Exception as e:
                    print(f"  ERROR: {e}")
                    results.append({
                        "case_id": case["id"],
                        "run_id": run_id,
                        "input": case["input"],
                        "category": case.get("category", "unknown"),
                        "node_outputs": {},
                        "final_state": {},
                        "error": str(e),
                    })
        return results
