from agents.base import BaseAgent, agent_log
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from memory.episodic import EpisodicMemory
from config import EPISODIC_DB_PATH, EPISODIC_SEARCH_LIMIT


class MemoryAgent(BaseAgent):
    def __init__(self, short_term: ShortTermMemory = None):
        super().__init__(name="Memory", system_prompt="你是记忆管理专家。")
        self.short_term = short_term or ShortTermMemory()
        self.long_term = LongTermMemory()
        self.episodic = EpisodicMemory(db_path=EPISODIC_DB_PATH)

    def __call__(self, state):
        query = state.get("context", {}).get("intent", "")
        if not query:
            query = state.get("context", {}).get("raw_response", "")

        agent_log("Memory", "三层记忆检索中...", f"检索关键词: {query[:100]}")

        # --- 短期记忆：最近对话上下文 ---
        recent = self.short_term.get_messages()
        short_term_context = ""
        if recent:
            lines = []
            for msg in recent[-5:]:  # 最近 5 轮
                lines.append(f"用户: {msg['human']}")
                lines.append(f"AI: {msg['ai']}")
            short_term_context = "\n".join(lines)
            agent_log("Memory", "短期记忆", f"最近 {len(recent)} 轮对话")

        # --- 长期记忆：Chroma 向量语义检索 ---
        long_term_result = ""
        try:
            if query:
                long_term_result = self.long_term.retrieve(query)
        except Exception:
            long_term_result = ""

        if long_term_result:
            agent_log("Memory", "长期记忆命中", long_term_result[:200])
        else:
            agent_log("Memory", "长期记忆无匹配")

        # --- 情景记忆：SQLite 历史任务检索 ---
        episodic_result = ""
        try:
            if query:
                episodes = self.episodic.search(query[:50], limit=EPISODIC_SEARCH_LIMIT)
                if episodes:
                    parts = []
                    for ep in episodes:
                        parts.append(
                            f"[{ep['ts']}] 任务: {ep['task']}\n"
                            f"结果: {ep['result']}\n"
                            f"经验: {', '.join(ep['lessons'])}"
                        )
                    episodic_result = "\n---\n".join(parts)
                    agent_log("Memory", "情景记忆命中", f"找到 {len(episodes)} 条历史任务")
        except Exception:
            episodic_result = ""

        # --- 合并三层记忆结果 ---
        sections = []
        if short_term_context:
            sections.append(f"[最近对话]\n{short_term_context}")
        if long_term_result:
            sections.append(f"[相关知识/经验]\n{long_term_result}")
        if episodic_result:
            sections.append(f"[历史任务记录]\n{episodic_result}")

        memory_result = "\n\n".join(sections) if sections else ""

        if memory_result:
            agent_log("Memory", "记忆检索完成", f"共 {len(sections)} 层记忆命中")
        else:
            agent_log("Memory", "无相关记忆")

        return {
            "memory_result": memory_result,
            "short_term_context": short_term_context,
        }

    def store(self, text: str, metadata: dict = None):
        """存储到长期记忆"""
        self.long_term.store(text, metadata or {})
