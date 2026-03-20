# P2 → P3 实施计划：Learner 反馈闭环 + Prompt 自优化

## 目标
让系统能从历史执行中**真正改进**，而不是 Learner 空转。

## 现状分析
- `LearnerAgent`：能提取经验写入长期记忆和情景记忆，但质量不可控，且 `learning/` 下三个模块（FeedbackCollector、PromptOptimizer、StrategyStore）**完全未接入**
- `FeedbackCollector`：纯内存 list，无持久化，未被调用
- `PromptOptimizer`：能存取 prompt patch 到 JSON 文件，未被调用
- `StrategyStore`：能存取策略到 JSON 文件，未被调用

## 实施步骤

### 步骤 1：接入 FeedbackCollector — 自动收集系统反馈
在 `main.py` 的主循环中，每轮任务执行完后自动收集反馈（任务是否成功、是否有错误），写入 FeedbackCollector。

修改文件：`main.py`

### 步骤 2：接入 StrategyStore — Learner 提取策略并持久化
让 LearnerAgent 在提取经验后，将成功策略写入 StrategyStore（JSON 持久化），而不是只存到 Chroma 向量库。

修改文件：`agents/learner.py`

### 步骤 3：接入 PromptOptimizer — Learner 生成 Prompt 改进建议
让 LearnerAgent 的 prompt 输出中增加 `prompt_patch` 字段，提取 Prompt 改进建议并存入 PromptOptimizer。

修改文件：`agents/learner.py`

### 步骤 4：BaseAgent 加载 Prompt Patches — 动态增强 system prompt
让 BaseAgent 在初始化时从 PromptOptimizer 加载已有的 patches，追加到 system_prompt 末尾，实现 prompt 自优化闭环。

修改文件：`agents/base.py`、`config.py`（添加 prompt patches 文件路径配置）

### 步骤 5：MemoryAgent recall 阶段融入策略检索
让 MemoryAgent 在 recall 时除了检索长期记忆和情景记忆，也从 StrategyStore 中搜索相关策略，一起提供给 Planner。

修改文件：`agents/memory_agent.py`

### 步骤 6：清理已知问题
- 删除 `should_continue` 中的死代码（第28-29行重复代码）
- 确保 Planner prompt 的绝对规则（计划末尾必须有终止工具）生效

修改文件：`orchestrator/core.py`

## 闭环效果
```
执行任务 → FeedbackCollector 收集结果
         → LearnerAgent 提取经验
              → StrategyStore 存储成功策略
              → PromptOptimizer 存储 prompt 改进
              → 长期记忆 + 情景记忆

下次任务 → MemoryAgent 检索策略 + 记忆
         → BaseAgent 加载 prompt patches
         → Planner 参考策略和改进后的 prompt 做规划
```
