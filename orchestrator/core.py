from langgraph.graph import StateGraph, END
from orchestrator.state import AgentState
from agents.perception import PerceptionAgent
from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent
from agents.memory_agent import MemoryAgent
from agents.learner import LearnerAgent
from memory.short_term import ShortTermMemory

# 创建共享的短期记忆实例，跨轮次保留
shared_short_term = ShortTermMemory()
memory_agent = MemoryAgent(short_term=shared_short_term)
learner_agent = LearnerAgent(memory_agent)


def should_continue(state) -> str:
    print(f"\n[DEBUG] current_step: {state['current_step']}, len(plan): {len(state['plan'])}")
    if state["tool_results"]:
        last_tool = state["tool_results"][-1].get("tool", "")
        print(f"[DEBUG] last_tool: {last_tool}")
        if last_tool in ["task_complete", "reply_user"]:
            return "learn"
        if state["tool_results"][-1].get("error"):
            return "replan"
            
    if state["current_step"] < len(state["plan"]):
        return "next_step"
    # 如果当前计划执行完了但没触发 task_complete，说明任务还未完成，回 plan 继续规划
    return "replan"



def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("perceive", PerceptionAgent())
    graph.add_node("recall", memory_agent)
    graph.add_node("plan", PlannerAgent())
    graph.add_node("execute", ExecutorAgent())
    graph.add_node("learn", learner_agent)

    graph.set_entry_point("perceive")
    graph.add_edge("perceive", "recall")
    graph.add_edge("recall", "plan")
    graph.add_edge("plan", "execute")
    graph.add_conditional_edges("execute", should_continue, {
        "next_step": "execute",
        "replan": "plan",
        "learn": "learn",
    })
    graph.add_edge("learn", END)

    return graph.compile()
