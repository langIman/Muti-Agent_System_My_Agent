# P1 → P2 实施计划：Chroma 向量记忆 + 三层记忆架构，跨会话记忆生效

## 目标
构建三层记忆架构（短期/长期/情景），让 Agent 具备跨会话的记忆能力。

## 现状分析（P1 完成后）
- Executor 已能调用真实工具完成任务
- MemoryAgent 和 LearnerAgent 存在但没有实际记忆存储后端
- 没有记忆检索能力，Planner 每次都从零开始规划

## 实施步骤

### 步骤 1：实现短期记忆 (memory/short_term.py)
基于 `deque` 实现 `ShortTermMemory`，滑动窗口保留最近 N 轮对话（配置项 `MEMORY_WINDOW_SIZE`）。提供 `add(human, ai)` 和 `get_context()` 方法。

### 步骤 2：实现长期记忆 (memory/long_term.py)
基于 ChromaDB 向量数据库实现 `LongTermMemory`，支持：
- `store(text, metadata)` — 写入向量化文本
- `search(query, top_k)` — 语义检索最相关的记忆

配置持久化目录 `CHROMA_DIR`。

### 步骤 3：实现情景记忆 (memory/episodic.py)
基于 SQLite 实现 `EpisodicMemory`，存储结构化的任务执行历史：
- 字段：task、result、lessons、timestamp
- 提供 `add()` 写入和 `search(keyword)` 关键词检索

配置数据库路径 `EPISODIC_DB_PATH`。

### 步骤 4：实现 MemoryAgent (agents/memory_agent.py)
创建 MemoryAgent，在 recall 阶段从三层记忆中检索：
- 短期记忆：取最近几轮对话
- 长期记忆：用 intent 做向量语义检索
- 情景记忆：用 intent 做 LIKE 关键词匹配

合并结果写入 `state["memory_result"]`，供 Planner 参考。

### 步骤 5：LearnerAgent 接入记忆写入
修改 LearnerAgent，在任务结束后：
- 将提取的经验写入长期记忆（Chroma）
- 将任务摘要写入情景记忆（SQLite）

### 步骤 6：主循环接入短期记忆
在 `main.py` 的主循环中，每轮对话结束后调用 `short_term_memory.add()` 记录对话。

### 步骤 7：Orchestrator 注册 MemoryAgent
在 `orchestrator/core.py` 中：
- 创建共享的 ShortTermMemory 实例
- 将 MemoryAgent 注册为 `recall` 节点
- 确保 perceive → recall → plan 的流转正确

### 步骤 8：添加配置项 (config.py)
添加记忆相关配置：`CHROMA_DIR`、`MEMORY_WINDOW_SIZE`、`RETRIEVER_TOP_K`、`EPISODIC_DB_PATH`、`EPISODIC_SEARCH_LIMIT`。

## 预期产出
- 三层记忆架构完整运行
- 跨会话记忆生效：上一轮对话的经验能在下一轮被检索出来
- Planner 能参考历史记忆做更好的规划
