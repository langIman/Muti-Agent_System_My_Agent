"""LLM-as-Judge：用 LLM 对 Agent 执行过程进行主观质量评分。"""
import json
from langchain_openai import ChatOpenAI
from config import MODEL_NAME, OPENAI_BASE_URL, OPENAI_API_KEY

JUDGE_PROMPT = """你是一位 AI 系统评估专家。请对以下多智能体系统的执行过程进行评分。

## 用户请求
{user_input}

## 感知结果（Perceiver 输出）
{perceiver_output}

## 执行计划（Planner 输出）
{plan}

## 工具执行结果
{tool_results}

## 最终回复
{reply}

## 评分维度（1-5 分，5 分最优）

1. **intent_accuracy**: 感知 Agent 是否准确理解了用户意图？
2. **plan_quality**: 计划是否合理、高效、完整？步骤是否必要且充分？
3. **task_fulfillment**: 最终是否满足了用户需求？任务完成度如何？
4. **response_quality**: 最终回复的质量——准确性、有用性、完整性、语言是否自然？

## 输出格式
严格输出 JSON，不要包含其他文字：
{{"intent_accuracy": N, "plan_quality": N, "task_fulfillment": N, "response_quality": N, "reasoning": "一句话总体评价"}}"""


class LLMJudge:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=MODEL_NAME,
            base_url=OPENAI_BASE_URL,
            api_key=OPENAI_API_KEY,
            temperature=0.0,
        )

    def score(self, user_input: str, node_outputs: dict, final_state: dict) -> dict:
        """对一次执行结果打分，返回各维度分数。"""
        perceiver_output = str(node_outputs.get("perceive", {}).get("context", {}))
        # plan 是列表（可能多次 replan），收集所有 plan 步骤
        plan_list = node_outputs.get("plan", [])
        all_plans = [po.get("plan", []) for po in plan_list] if isinstance(plan_list, list) else []
        plan_output = str(all_plans)
        tool_results = str(final_state.get("tool_results", []))[:3000]

        # 提取最终回复
        reply = ""
        for tr in final_state.get("tool_results", []):
            if tr.get("tool") in ("reply_user", "task_complete"):
                reply = tr.get("result", "")

        if not reply:
            msgs = final_state.get("messages", [])
            if msgs:
                last = msgs[-1]
                reply = getattr(last, "content", str(last))[:500]

        prompt = JUDGE_PROMPT.format(
            user_input=user_input,
            perceiver_output=perceiver_output[:1000],
            plan=plan_output[:1500],
            tool_results=tool_results,
            reply=reply[:1000],
        )

        try:
            result = self.llm.invoke([("user", prompt)])
            text = result.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            scores = json.loads(text)
            return scores
        except Exception as e:
            return {"error": str(e), "raw": getattr(result, "content", "")}
