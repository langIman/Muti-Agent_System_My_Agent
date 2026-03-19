import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config import MODEL_NAME, OPENAI_BASE_URL, OPENAI_API_KEY
#testtesttest

# ANSI 颜色
COLORS = {
    "Perceiver": "\033[36m",   # 青色
    "Memory":    "\033[35m",   # 紫色
    "Planner":   "\033[33m",   # 黄色
    "Executor":  "\033[32m",   # 绿色
    "Learner":   "\033[34m",   # 蓝色
}
RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"


def agent_log(agent_name: str, message: str, detail: str = ""):
    """打印 Agent 工作流日志"""
    color = COLORS.get(agent_name, "\033[37m")
    print(f"\n{color}{BOLD}{'─' * 50}")
    print(f"🤖 [{agent_name}] {message}")
    print(f"{'─' * 50}{RESET}")
    if detail:
        # 缩进详情，限制长度
        for line in detail[:500].split("\n"):
            print(f"  {color}{DIM}{line}{RESET}")
        if len(detail) > 500:
            print(f"  {color}{DIM}... (已截断){RESET}")


class BaseAgent:
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.llm = ChatOpenAI(
            model=MODEL_NAME,
            base_url=OPENAI_BASE_URL,
            api_key=OPENAI_API_KEY,
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("placeholder", "{messages}"),
        ])
        self.chain = self.prompt | self.llm

    def __call__(self, state: dict) -> dict:
        response = self.chain.invoke(state)
        return {"messages": [response]}


def parse_json(text: str):
    """从 LLM 输出中提取 JSON。"""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}