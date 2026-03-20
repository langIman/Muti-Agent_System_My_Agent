# P3 → P4 实施计划：单 Agent 优化

## 目标
在现有框架稳定的基础上，逐步优化各 Agent 的工作质量，减少噪音、提升决策准确性。

## 已识别的优化方向

### 优化 1：各 Agent 去除无效 messages 历史注入
**问题**：`BaseAgent` 通过 `("placeholder", "{messages}")` 把完整对话历史注入每个 Agent，但只有 Perception 需要历史上下文，其他 Agent 接收历史只会引入噪音。

**目标**：
- Planner / Executor / MemoryAgent / Learner 各自定制 prompt，只注入真正需要的字段
- BaseAgent 的通用模板仅作为 Perception 的基础，其他 Agent 各自 override

修改文件：`agents/base.py`、`agents/planner.py`、`agents/learner.py`、`agents/memory_agent.py`

---

### 优化 2：Perception 感知工具升级
**问题**：`get_system_info` 只返回 OS 和 Python 版本，信息几乎不变且后续节点从未使用，无实际价值。

**目标**：替换为真正有用的环境感知工具，例如：
- 当前工作目录
- 可用工具列表
- 当前时间 / 日期

修改文件：`agents/perception.py`

---

### 优化 3：Agent 严格解耦（单一职责）
**问题**：多 Agent 系统中各 Agent 职责边界不清晰，任何 Agent 都可能持有工具调用能力，导致行为难以预测、出错时难以定位。

**核心认知**：
- 感知、规划、记忆、学习都是**纯推理**行为，不需要执行任何外部动作
- 文件路径、网络请求等"执行细节"是 Executor 的唯一职责
- 工具调用统一收敛到 Executor，出问题时定位清晰

**目标**：确保所有 Agent 严格遵守单一职责，工具调用只发生在 Executor：

| Agent | 职责 | 是否可调用工具 |
|-------|------|----------------|
| Perception | 解析用户意图 | ❌ |
| MemoryAgent | 检索/写入记忆 | ❌ |
| Planner | 生成执行步骤 | ❌ |
| Executor | 执行工具调用 | ✅ |
| Learner | 提取经验/优化策略 | ❌ |

**具体修改**：
- 移除 `PerceptionAgent` 的 `bind_tools`、`tools_map`
- 检查其余 Agent 是否有隐式工具绑定，一并清理
- 系统环境信息改为静态上下文注入 prompt，不通过工具获取

修改文件：`agents/perception.py`、`agents/base.py` 及其他存在工具绑定的 Agent

---

## 实施状态

| 优化项 | 状态 | 修改文件 |
|--------|------|----------|
| 优化 1：去除无效 messages 历史注入 | ✅ 已完成 | `agents/base.py`, `agents/planner.py`, `agents/learner.py`, `agents/memory_agent.py` |
| 优化 2：Perception 感知工具升级 | ✅ 已完成 | `agents/perception.py` |
| 优化 3：Agent 严格解耦 | ✅ 已完成 | `agents/perception.py`, `agents/base.py` |

> 后续优化方向持续补充...
