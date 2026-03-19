# P1 → P2 阶段遇到的问题

## 1. should_continue 死循环
**用户指令：** "你自己搜索一条伊朗新闻插到文件中，自己想想应该插到哪个文件"
**现象：** Agent 在 Planner 生成计划 → Executor 执行 → 重新规划 之间无限循环。
**原因：** Planner 生成的计划中没有包含 `task_complete` 或 `reply_user` 终止工具，导致计划执行完后 `should_continue` 始终返回 `"replan"`。
**解决思路：** 在 Planner 的 prompt 中强制要求计划末尾包含终止工具。
**备注：** 曾尝试添加 `MAX_REPLAN_TIMES` 限制重规划次数强制进入 learn，但被回滚——因为这会破坏「执行→观察→规划→执行」的范式。

## 2. Executor 不严格按 Planner 计划执行
**用户指令：** 同上（搜索伊朗新闻插入文件）
**现象：** Executor（LLM 驱动）会对 Planner 的步骤做自主拆分和微调，有"自己的想法"。
**原因：** Planner 输出的是自然语言描述而非精确工具调用参数，LLM 驱动的 Executor 在解释执行时会自主发挥。
**解决思路：** 保持现状。如果要严格执行，需要把 Planner 输出改为精确工具调用参数，Executor 变成纯 dispatcher，但会失去灵活性。
**备注：** 属于设计取舍，暂不改动。最终任务仍然完成了，Executor 本质上是把 Planner 的步骤拆分成了更细粒度的操作。

## 3. 记忆模块干扰 Planner 决策
**用户指令：** "你自己搜索一条伊朗新闻插到文件中，自己想想应该插到哪个文件"
**现象：** 意图明确的指令，Agent 反而调用 reply_user 工具向用户确认，过于依赖记忆模块。
**原因：** MemoryAgent 检索出的低质量或不相关记忆影响了 Planner 的判断。
**解决思路：** 需要解决记忆写入质量和读取筛选两个问题，让 Planner 能区分哪些记忆该参考、哪些该忽略。
**备注：** 待优化，属于 P3 阶段的改进方向。

## 4. Learner 模块正向作用微弱
**用户指令：** 多轮对话观察后发现
**现象：** Learner 能跑通流程（提取经验、保存情景记忆），但提取的经验质量不可控，`lesson_list` 可能为空，learning 文件夹下的 FeedbackCollector、PromptOptimizer、StrategyStore 均未接入。
**原因：** Learner 的 prompt 对经验提取的质量缺乏约束；`parse_json` 解析失败时静默返回空结果；learning 模块尚未集成。
**解决思路：** P3 阶段接入 Learner 反馈闭环 + Prompt 自优化，提升经验提取质量。
**备注：** Learner 目前是架构占位符，保证 plan→execute→learn 流程完整，但 learn 环节尚未产生真正闭环效果。