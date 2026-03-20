# P4 → P5 实施计划：评估体系 + 运行时优化

## 目标
建立三层评估体系量化 Agent 能力，同时修复运行时暴露的问题、优化各 Agent 的执行质量。

---

## 已完成的优化

### 优化 1：三层评估框架
**问题**：P4 完成后无法量化各 Agent 的能力，缺乏回归测试手段。

**方案**：
- **结构化指标**（`eval/metrics/structural.py`）：自动检查 JSON 格式、工具名合法性、计划终止条件等
- **LLM-as-Judge**（`eval/metrics/llm_judge.py`）：用 LLM 对 4 个维度打 1-5 分（意图准确度、计划质量、任务完成度、回复质量）
- **Benchmark 测试集**（`eval/test_cases.yaml`）：5 类场景 10 个声明式用例，支持多次运行防退化
- **零侵入设计**：用 `graph.stream()` 捕获每个节点输出，不修改任何 Agent 代码

新增文件：`eval/` 目录（harness.py, run_eval.py, report.py, metrics/, test_cases.yaml）

| 状态 | ✅ 已完成 |
|------|----------|

---

### 优化 2：修复空计划崩溃
**问题**：用户输入"哈喽"时，Planner 生成 0 步计划，Executor 用 `state["plan"][state["current_step"]]` 索引空列表导致 `IndexError`。

**修复**：
- **Planner fallback**（`agents/planner.py`）：JSON 解析失败时生成 `reply_user` 步骤，而非无效的 `tool: "none"`
- **Executor 防御**（`agents/executor.py`）：`current_step` 越界时安全返回，不再崩溃

修改文件：`agents/planner.py`, `agents/executor.py`

| 状态 | ✅ 已完成 |
|------|----------|

---

### 优化 3：Planner 探索计划模式（观察→计划→执行→观察）
**问题**：Planner prompt 强制"每个计划最后一步必须是 reply_user/task_complete"，导致必须一次性生成完整计划，无法先探索再决策，不符合迭代推理范式。

**修复**：
- 引入两种计划模式：
  - **完整计划**：信息充足时一步到位，以终止工具结尾
  - **探索计划**：需要先执行几步看结果，不加终止工具，系统自动触发 replan
- `should_continue` 已原生支持：计划执行完无终止工具 → 走 replan 路径
- 向 Planner 注入当前 replan 次数，让其合理分配探索预算

修改文件：`agents/planner.py`

| 状态 | ✅ 已完成 |
|------|----------|

---

### 优化 4：Learner 质量过滤
**问题**：简单任务（问候、纯问答）也调 LLM 生成经验，产出"step 编号错位"等低质量 lesson 污染长期记忆。

**修复**：
- 简单任务检测：如果 `tool_results` 中所有 tool 都是 `reply_user`/`task_complete`（无实质工具调用），跳过 LLM 调用
- 仍写入情景记忆（保留任务记录），但不产出 lesson/strategy/prompt_patch

修改文件：`agents/learner.py`

| 状态 | ✅ 已完成 |
|------|----------|

---

### 优化 5：Memory 检索相关性阈值过滤
**问题**：Chroma `as_retriever()` 总返回 top-K 结果，即使相似度极低也返回，导致"你好"检索到"工具调用前必须验证文件"这种无关噪声。

**修复**：
- 改用 `similarity_search_with_relevance_scores()`，只保留 score >= 0.35 的结果
- `config.py` 新增 `RELEVANCE_THRESHOLD = 0.35`
- 效果：问候场景从返回 5 条无关噪声缩减到 1 条相关内容

修改文件：`memory/long_term.py`, `config.py`

| 状态 | ✅ 已完成 |
|------|----------|
