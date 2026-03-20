"""结构化指标：对每个 Agent 的输出做自动化格式/规则校验。"""
import json

VALID_TOOLS = {
    "web_search", "execute_python", "read_file", "write_file",
    "list_directory", "find_file", "api_call", "reply_user", "task_complete",
}


def _parse_json(text: str):
    """从 LLM 输出中提取 JSON（复用 agents/base.py 的逻辑）。"""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except (json.JSONDecodeError, IndexError):
        return {}


def check_perceiver(node_output: dict, expect: dict) -> dict:
    """检查 Perceiver 输出的结构有效性。"""
    results = {}
    context = node_output.get("context", {})
    raw = context.get("raw_response", "")

    # JSON 解析成功
    parsed = _parse_json(raw) if isinstance(raw, str) else raw
    results["json_valid"] = {"passed": bool(parsed), "value": type(parsed).__name__}

    # intent 非空
    intent = parsed.get("intent", "")
    results["has_intent"] = {"passed": bool(intent), "value": intent}

    # needs_tools 只包含合法工具名
    needs_tools = parsed.get("needs_tools", [])
    if isinstance(needs_tools, list):
        invalid = [t for t in needs_tools if t not in VALID_TOOLS]
        results["valid_tools"] = {"passed": len(invalid) == 0, "value": invalid}
    else:
        results["valid_tools"] = {"passed": False, "value": "not a list"}

    # 期望检查
    if "needs_tools" in expect:
        results["expected_tools"] = {
            "passed": set(needs_tools) == set(expect["needs_tools"]),
            "value": needs_tools,
            "expected": expect["needs_tools"],
        }

    if "needs_tools_contains" in expect:
        expected_set = set(expect["needs_tools_contains"])
        actual_set = set(needs_tools)
        results["tools_contains"] = {
            "passed": expected_set.issubset(actual_set),
            "value": needs_tools,
            "expected": expect["needs_tools_contains"],
        }

    return results


def check_planner(plan_outputs: list, expect: dict) -> dict:
    """检查 Planner 输出的结构有效性。

    plan_outputs: 所有 plan 节点输出的列表（replan 会产生多次）。
    检查基于最终 plan，但 contains_tool 跨所有 plan 检查。
    """
    results = {}

    if not plan_outputs:
        results["non_empty"] = {"passed": False, "value": 0}
        return results

    # 取最终 plan 做格式检查
    last_output = plan_outputs[-1]
    plan = last_output.get("plan", [])

    results["is_list"] = {"passed": isinstance(plan, list), "value": type(plan).__name__}

    if not isinstance(plan, list) or len(plan) == 0:
        results["non_empty"] = {"passed": False, "value": 0}
        return results

    results["non_empty"] = {"passed": True, "value": len(plan)}

    # 最后一步是终止工具
    last_tool = plan[-1].get("tool", "")
    results["terminal_tool"] = {
        "passed": last_tool in ("reply_user", "task_complete"),
        "value": last_tool,
    }

    # 所有工具名合法（仅检查最终 plan）
    plan_tools = [s.get("tool", "") for s in plan]
    invalid = [t for t in plan_tools if t not in VALID_TOOLS and t != "none"]
    results["valid_tools"] = {"passed": len(invalid) == 0, "value": invalid}

    # 收集所有 plan 中出现的工具（用于 contains_tool）
    all_plan_tools = []
    for po in plan_outputs:
        for step in po.get("plan", []):
            all_plan_tools.append(step.get("tool", ""))

    # 期望检查
    if "max_steps" in expect:
        results["max_steps"] = {"passed": len(plan) <= expect["max_steps"], "value": len(plan)}

    if "min_steps" in expect:
        results["min_steps"] = {"passed": len(plan) >= expect["min_steps"], "value": len(plan)}

    if "last_tool_in" in expect:
        results["last_tool_in"] = {
            "passed": last_tool in expect["last_tool_in"],
            "value": last_tool,
            "expected": expect["last_tool_in"],
        }

    if "contains_tool" in expect:
        target = expect["contains_tool"]
        results["contains_tool"] = {
            "passed": target in all_plan_tools,
            "value": all_plan_tools,
            "expected": target,
        }

    return results


def check_executor(tool_results: list, expect: dict) -> dict:
    """检查 Executor 执行结果。"""
    results = {}

    # 排除 reply_user/task_complete（这些不是真正的工具执行）
    real_results = [tr for tr in tool_results if tr.get("tool") not in ("reply_user", "task_complete")]
    errors = [tr for tr in real_results if tr.get("error")]

    total = len(real_results)
    success = total - len(errors)
    rate = success / total if total > 0 else 1.0

    results["total_calls"] = {"passed": True, "value": total}
    results["error_count"] = {"passed": True, "value": len(errors)}
    results["success_rate"] = {"passed": True, "value": f"{rate:.0%}"}

    if expect.get("no_errors"):
        results["no_errors"] = {
            "passed": len(errors) == 0,
            "value": [e.get("error", "") for e in errors],
        }

    if expect.get("has_error"):
        results["has_error"] = {"passed": len(errors) > 0, "value": len(errors)}

    return results


def check_learner(node_output: dict) -> dict:
    """检查 Learner 输出的结构有效性。"""
    results = {}
    feedback = node_output.get("feedback", {})

    results["has_feedback"] = {"passed": bool(feedback), "value": type(feedback).__name__}

    if not feedback:
        return results

    # 有 lessons 字段
    lessons = feedback.get("lessons", [])
    results["has_lessons"] = {"passed": isinstance(lessons, list), "value": type(lessons).__name__}

    # 幻觉检测：lessons 里包含 plan step 格式的条目
    if isinstance(lessons, list):
        hallucinated = [l for l in lessons if isinstance(l, dict) and "step" in l]
        results["no_hallucination"] = {
            "passed": len(hallucinated) == 0,
            "value": len(hallucinated),
        }

    return results


def check_end_to_end(final_state: dict, expect: dict) -> dict:
    """检查端到端结果。"""
    results = {}
    tool_results = final_state.get("tool_results", [])
    replan_count = final_state.get("replan_count", 0)

    # 提取最终回复
    reply = ""
    for tr in tool_results:
        if tr.get("tool") in ("reply_user", "task_complete"):
            reply = tr.get("result", "")

    results["has_reply"] = {"passed": bool(reply), "value": reply if reply else "(empty)"}
    results["replan_count"] = {"passed": True, "value": replan_count}

    if "max_replans" in expect:
        results["max_replans"] = {
            "passed": replan_count <= expect["max_replans"],
            "value": replan_count,
        }

    if expect.get("has_reply"):
        results["expected_reply"] = {"passed": bool(reply), "value": bool(reply)}

    if "reply_contains" in expect:
        target = expect["reply_contains"]
        results["reply_contains"] = {
            "passed": target.lower() in reply.lower(),
            "value": reply[:200],
            "expected": target,
        }

    return results
