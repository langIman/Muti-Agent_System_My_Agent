# P3 → P4 问题与解决记录

## 优化 1：去除无效 messages 历史注入

### 问题
`BaseAgent` 通过 `("placeholder", "{messages}")` 把完整对话历史注入每个 Agent。多轮对话后，messages 中累积了大量无关消息（Perception 的 AIMessage、历史 HumanMessage 等），对 Planner/Learner 而言是纯噪音。

### 解决方案
1. `BaseAgent` 新增 `use_messages` 参数，控制是否在 prompt 模板中包含 `{messages}` 占位符
2. `extract_user_request()` 辅助函数：从 state 中提取用户原始请求
3. 各 Agent 定制化消息注入：
   - **Perception**: `use_messages=True` — 需要对话历史理解用户意图
   - **MemoryAgent**: `use_messages=False` — 纯代码逻辑，不使用 LLM chain
   - **Planner**: 自行构建干净消息（用户请求 + 感知上下文 + 记忆 + replan 时的工具结果）
   - **Executor**: 已有独立消息构建（无变动）
   - **Learner**: 自行构建干净消息（用户请求 + 执行计划 + 工具结果）

### 效果
Planner 和 Learner 不再收到累积的对话垃圾，推理质量更稳定。

---

## 优化 2：Perception 感知工具升级

### 问题
`get_system_info` 工具只返回 OS 和 Python 版本，信息几乎不变且后续节点从未使用。

### 解决方案
替换为静态环境上下文注入 system prompt：
- 当前工作目录 (`os.getcwd()`)
- 可用工具列表 (`ALL_TOOLS` 名称)
- 当前时间（每次调用动态注入为 system message）

### 效果
Perception 获得真正有用的环境信息，且无需通过工具调用获取。

---

## 优化 3：Agent 严格解耦（单一职责）

### 问题
`PerceptionAgent` 绑定了 `get_system_info` 工具并通过 `bind_tools` 赋予了工具调用能力。这违反了"只有 Executor 才能调用工具"的原则。

### 解决方案
1. 移除 `PerceptionAgent` 的 `self.tools`、`self.tools_map`、`self.llm.bind_tools()`
2. 移除 `get_system_info` 工具定义
3. 移除对 `platform`、`langchain_core.tools`、`langchain_core.messages.ToolMessage` 的导入
4. 环境信息改为静态上下文（见优化 2）

### 效果
Agent 职责彻底清晰：

| Agent | 职责 | 工具调用 |
|-------|------|----------|
| Perception | 解析用户意图 | ❌ 纯推理 |
| MemoryAgent | 检索/写入记忆 | ❌ 纯代码 |
| Planner | 生成执行步骤 | ❌ 纯推理 |
| Executor | 执行工具调用 | ✅ 唯一 |
| Learner | 提取经验/优化 | ❌ 纯推理 |

---

## 实施中遇到的小问题

### 中文引号编码问题
**现象**: 重写 `planner.py` 时，原文中的中文左右引号 `\u201c` `\u201d` 被转为 ASCII `"`，导致 Python 字符串提前终止产生 SyntaxError。

**解决**: 使用 Unicode 转义 `\u201c` / `\u201d` 替代字面中文引号。
