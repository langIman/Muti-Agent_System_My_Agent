from agents.base import BaseAgent, parse_json, agent_log
from memory.episodic import EpisodicMemory
from config import EPISODIC_DB_PATH


class LearnerAgent(BaseAgent):
    def __init__(self, memory_agent):
        super().__init__(
            name="Learner",
            system_prompt=(
                "你是学习专家。你的唯一职责是对刚才的执行过程进行**事后复盘总结**，**绝对不要**尝试生成下一步的执行计划或代码！\n"
                "分析任务执行过程，提取：\n"
                "1. 成功策略（可复用的模式）\n"
                "2. 失败教训（应避免的做法）\n"
                "输出 JSON: {{\"lessons\": [\"用一句话总结的经验1\", \"用一句话总结的经验2\"], \"summary\": \"整体复盘总结\"}}\n"
                "注意：lessons 数组里只能是总结性的文本，绝对不能包含具体的操作步骤或 API 调用！"
            ),
        )
        self.memory = memory_agent
        self.episodic = EpisodicMemory(db_path=EPISODIC_DB_PATH)

    def __call__(self, state):
        agent_log("Learner", "分析执行过程，提取经验...")

        result = self.chain.invoke(state)
        lessons = parse_json(result.content)

        # 兼容 LLM 返回 list 或 dict 格式
        if isinstance(lessons, list):
            lessons = {"lessons": lessons, "summary": ""}

        lesson_list = lessons.get("lessons", [])
        summary = lessons.get("summary", "")

        # 过滤有效经验并存入长期记忆
        valid_lessons = []
        if lesson_list:
            agent_log("Learner", f"提取了 {len(lesson_list)} 条经验")
            for i, lesson in enumerate(lesson_list, 1):
                if isinstance(lesson, dict) and "step" in lesson:
                    agent_log("Learner", "⚠️ 警告：检测到幻觉生成的计划步骤，已丢弃该无用经验。")
                    continue
                lesson_str = lesson if isinstance(lesson, str) else str(lesson)
                valid_lessons.append(lesson_str)
                print(f"  \033[34m  📝 {i}. {lesson_str[:100]}\033[0m")
                self.memory.store(lesson_str, metadata={"type": "lesson"})
        if summary:
            agent_log("Learner", "任务总结", summary)

        # --- 写入情景记忆 ---
        task_desc = state.get("context", {}).get("intent", "")
        if not task_desc:
            task_desc = state.get("context", {}).get("raw_response", "未知任务")
        task_result = summary or "已完成"

        try:
            self.episodic.add(
                task=task_desc,
                result=task_result,
                lessons=valid_lessons,
            )
            agent_log("Learner", "情景记忆已保存", f"任务: {task_desc[:80]}")
        except Exception as e:
            agent_log("Learner", "情景记忆写入失败", str(e))

        return {"messages": [result], "feedback": lessons}
