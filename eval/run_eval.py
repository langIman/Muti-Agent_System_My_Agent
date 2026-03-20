#!/usr/bin/env python
"""
Agent 评估框架入口。

用法:
  python eval/run_eval.py                          # 跑全部用例
  python eval/run_eval.py --runs 3                 # 每个用例跑 3 次
  python eval/run_eval.py --category conversation   # 只跑某一类
  python eval/run_eval.py --no-judge               # 跳过 LLM 评分（省钱快速）
  python eval/run_eval.py --output eval/results/my_run.json
"""
import argparse
import json
import os
import sys

# 确保项目根目录在 sys.path 中
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import yaml
from eval.harness import EvalHarness
from eval.metrics.structural import (
    check_perceiver, check_planner, check_executor, check_learner, check_end_to_end,
)
from eval.report import EvalReport


def load_cases(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("cases", [])


def evaluate(raw_results: list, cases: list, use_judge: bool) -> list:
    """对原始执行结果进行结构化评估和 LLM 评分。"""
    judge = None
    if use_judge:
        from eval.metrics.llm_judge import LLMJudge
        judge = LLMJudge()

    case_map = {c["id"]: c for c in cases}
    evaluated = []

    for raw in raw_results:
        if raw.get("error"):
            evaluated.append(raw)
            continue

        case = case_map.get(raw["case_id"], {})
        expect = case.get("expect", {})
        node_outputs = raw.get("node_outputs", {})
        final_state = raw.get("final_state", {})

        # 结构化指标
        structural = {}

        if "perceive" in node_outputs:
            structural["perceiver"] = check_perceiver(
                node_outputs["perceive"], expect.get("perceiver", {})
            )

        # plan 节点可能因 replan 被多次调用，传入完整列表
        if "plan" in node_outputs:
            structural["planner"] = check_planner(
                node_outputs["plan"], expect.get("planner", {})
            )

        # executor 结果从 final_state 取
        structural["executor"] = check_executor(
            final_state.get("tool_results", []), expect.get("executor", {})
        )

        # learner
        if "learn" in node_outputs:
            structural["learner"] = check_learner(node_outputs["learn"])

        # 端到端
        structural["end_to_end"] = check_end_to_end(
            final_state, expect.get("end_to_end", {})
        )

        all_passed = all(
            m["passed"]
            for agent_metrics in structural.values()
            for m in agent_metrics.values()
        )

        result = {
            **raw,
            "structural_metrics": structural,
            "structural_all_passed": all_passed,
        }

        # LLM-as-Judge
        if judge:
            print(f"  Judging {raw['case_id']}...")
            scores = judge.score(raw["input"], node_outputs, final_state)
            result["judge_scores"] = scores

            # 校验评分阈值
            for dim, threshold_str in case.get("judge", {}).items():
                if not isinstance(threshold_str, str):
                    continue
                try:
                    op, val = threshold_str[:2], float(threshold_str[2:])
                    actual = scores.get(dim, 0)
                    if isinstance(actual, (int, float)):
                        if op == ">=":
                            result[f"judge_{dim}_ok"] = actual >= val
                except (ValueError, TypeError):
                    pass

        evaluated.append(result)

    return evaluated


def main():
    parser = argparse.ArgumentParser(description="Agent 评估框架")
    parser.add_argument("--runs", type=int, default=1, help="每个用例运行次数")
    parser.add_argument("--category", type=str, default=None, help="只跑某一类用例")
    parser.add_argument("--no-judge", action="store_true", help="跳过 LLM 评分")
    parser.add_argument("--cases", default=None, help="测试用例 YAML 路径")
    parser.add_argument("--output", default=None, help="结果 JSON 保存路径")
    args = parser.parse_args()

    # 默认路径
    if args.cases is None:
        args.cases = os.path.join(project_root, "eval", "test_cases.yaml")
    if args.output is None:
        args.output = os.path.join(project_root, "eval", "results", "latest.json")

    # 加载用例
    cases = load_cases(args.cases)
    print(f"加载了 {len(cases)} 个测试用例")

    categories = [args.category] if args.category else None
    if categories:
        print(f"过滤类别: {categories}")

    # 执行
    harness = EvalHarness(cases)
    raw_results = harness.run_all(num_runs=args.runs, categories=categories)

    # 评估
    print(f"\n{'='*60}")
    print("评估中...")
    print(f"{'='*60}")
    evaluated = evaluate(raw_results, cases, use_judge=not args.no_judge)

    # 保存结果
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(evaluated, f, ensure_ascii=False, default=str, indent=2)

    # 生成 Markdown 报告
    report = EvalReport(evaluated)
    md_content = report.generate()

    md_path = args.output.rsplit(".", 1)[0] + ".md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"\n结果已保存:")
    print(f"  JSON: {args.output}")
    print(f"  报告: {md_path}")
    #print(f"\n{md_content}")


if __name__ == "__main__":
    main()
