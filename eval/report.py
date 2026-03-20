"""评估报告生成器：输出 Markdown 格式报告。"""
from datetime import datetime


class EvalReport:
    def __init__(self, results: list):
        self.results = results

    def generate(self) -> str:
        lines = []
        total = len(self.results)
        passed = sum(1 for r in self.results if r.get("structural_all_passed", False))
        error_count = sum(1 for r in self.results if r.get("error"))

        lines.append("# Agent 评估报告")
        lines.append("")
        lines.append(f"> 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
        lines.append(f"> 结果: **{passed}/{total}** 通过, {error_count} 错误")
        lines.append("")

        # ── 分类汇总表 ──
        categories = {}
        for r in self.results:
            cat = r.get("category", "unknown")
            categories.setdefault(cat, []).append(r)

        lines.append("## 分类汇总")
        lines.append("")
        # 表头
        has_judge = any(r.get("judge_scores") for r in self.results)
        header = "| 类别 | 通过率 | 状态 |"
        sep = "|------|--------|------|"
        if has_judge:
            header = "| 类别 | 通过率 | 状态 | 意图准确 | 计划质量 | 任务完成 | 回复质量 |"
            sep = "|------|--------|------|----------|----------|----------|----------|"
        lines.append(header)
        lines.append(sep)

        for cat, cases in categories.items():
            cat_total = len(cases)
            cat_pass = sum(1 for c in cases if c.get("structural_all_passed", False))
            icon = "Pass" if cat_pass == cat_total else "Fail"
            row = f"| {cat} | {cat_pass}/{cat_total} | {icon} |"

            if has_judge:
                dims = {}
                for c in cases:
                    scores = c.get("judge_scores", {})
                    for d in ("intent_accuracy", "plan_quality", "task_fulfillment", "response_quality"):
                        v = scores.get(d)
                        if isinstance(v, (int, float)):
                            dims.setdefault(d, []).append(v)
                for d in ("intent_accuracy", "plan_quality", "task_fulfillment", "response_quality"):
                    vals = dims.get(d, [])
                    avg = f"{sum(vals)/len(vals):.1f}" if vals else "-"
                    row += f" {avg} |"
            lines.append(row)

        lines.append("")

        # ── 用例详情 ──
        lines.append("## 用例详情")
        lines.append("")

        for r in self.results:
            is_passed = r.get("structural_all_passed", False)
            error = r.get("error")
            if error:
                status = "ERROR"
                icon = "X"
            elif is_passed:
                status = "PASS"
                icon = "Pass"
            else:
                status = "FAIL"
                icon = "Fail"

            lines.append(f"### {icon} `{r['case_id']}` — {status}")
            lines.append("")
            lines.append(f"- **输入**: {r.get('input', '')}")
            lines.append(f"- **类别**: {r.get('category', '')}")
            lines.append("")

            if error:
                lines.append(f"> **错误**: {error}")
                lines.append("")
                continue

            # 结构指标表
            structural = r.get("structural_metrics", {})
            if structural:
                lines.append("| Agent | 指标 | 结果 | 值 |")
                lines.append("|-------|------|------|----|")
                reply_value = None
                for agent, metrics in structural.items():
                    for metric, val in metrics.items():
                        mark = "Pass" if val["passed"] else "**Fail**"
                        detail = val["value"]
                        # 最终回复单独展示，不放表格里
                        if agent == "end_to_end" and metric == "has_reply" and isinstance(detail, str) and len(detail) > 60:
                            reply_value = detail
                            detail = f"(见下方)"
                        elif isinstance(detail, str) and len(detail) > 60:
                            detail = detail[:60] + "..."
                        elif isinstance(detail, list) and len(str(detail)) > 60:
                            detail = str(detail)[:60] + "..."
                        lines.append(f"| {agent} | {metric} | {mark} | `{detail}` |")
                lines.append("")

                # 最终回复完整展示
                if reply_value:
                    lines.append("**最终回复:**")
                    lines.append("")
                    lines.append("<details>")
                    lines.append("<summary>点击展开</summary>")
                    lines.append("")
                    lines.append(reply_value)
                    lines.append("")
                    lines.append("</details>")
                    lines.append("")

            # LLM 评分
            scores = r.get("judge_scores", {})
            if scores and "error" not in scores:
                lines.append("**LLM 评分:**")
                lines.append("")
                lines.append("| 意图准确 | 计划质量 | 任务完成 | 回复质量 |")
                lines.append("|----------|----------|----------|----------|")
                row = "| "
                for d in ("intent_accuracy", "plan_quality", "task_fulfillment", "response_quality"):
                    v = scores.get(d, "?")
                    row += f"{v}/5 | "
                lines.append(row)
                reasoning = scores.get("reasoning", "")
                if reasoning:
                    lines.append(f"\n> {reasoning}")
                lines.append("")
            elif scores and "error" in scores:
                lines.append(f"> **LLM 评分错误**: {scores['error']}")
                lines.append("")

        return "\n".join(lines)
