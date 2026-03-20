import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config import MODEL_NAME, OPENAI_BASE_URL, OPENAI_API_KEY, PROMPT_PATCHES_PATH
from learning.prompt_optimizer import PromptOptimizer

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
    def __init__(self, name: str, system_prompt: str, use_messages: bool = True):
        """
        Args:
            name: Agent 名称
            system_prompt: 系统提示
            use_messages: 是否在 prompt 模板中注入 {messages} 对话历史。
                          只有需要读取对话上下文的 Agent 才设为 True。
        """
        self.name = name
        self.llm = ChatOpenAI(
            model=MODEL_NAME,
            base_url=OPENAI_BASE_URL,
            api_key=OPENAI_API_KEY,
        )
        # 加载 Prompt Patches 动态增强 system prompt
        optimizer = PromptOptimizer(path=PROMPT_PATCHES_PATH)
        patches = optimizer.get_patches(name)
        if patches:
            # 转义大括号，防止 LangChain 将其解析为模板变量
            patch_text = "\n".join(f"- {p}" for p in patches)
            patch_text = patch_text.replace("{", "{{").replace("}", "}}")
            system_prompt += f"\n\n## 历史改进建议（基于过往执行经验）\n{patch_text}"

        template_messages = [("system", system_prompt)]
        if use_messages:
            template_messages.append(("placeholder", "{messages}"))
        self.prompt = ChatPromptTemplate.from_messages(template_messages)
        self.chain = self.prompt | self.llm

    def __call__(self, state: dict) -> dict:
        response = self.chain.invoke(state)
        return {"messages": [response]}


def extract_user_request(state: dict) -> str:
    """从 state 中提取用户原始请求文本。"""
    messages = state.get("messages", [])
    if not messages:
        return ""
    # 找最后一条用户消息（当前轮次的输入）
    for msg in reversed(messages):
        if isinstance(msg, tuple) and msg[0] == "user":
            return msg[1]
        if hasattr(msg, "type") and msg.type == "human":
            return msg.content
    # fallback: 第一条消息
    first = messages[0]
    if isinstance(first, tuple):
        return first[1]
    return getattr(first, "content", str(first))


def parse_json(text: str):
    """从 LLM 输出中提取 JSON。"""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}