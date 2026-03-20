# P0 → P1 阶段遇到的问题

> 此阶段由终端 Claude 完成，以下为根据代码和架构推断的可能问题。

## 1. LLM 返回非标准 JSON 导致计划解析失败
**用户指令：** 任意需要 Planner 生成计划的指令
**现象：** Planner 返回的内容包含 markdown 代码块（如 ```json ... ```）或多余文本，`parse_json` 无法直接解析。
**原因：** LLM 倾向于用自然语言包裹 JSON 输出，而非纯 JSON。
**解决思路：** 在 `parse_json` 中增加正则提取，剥离 markdown 标记和多余文本。
**备注：** 这是 LLM 应用的常见问题，几乎所有依赖 LLM 输出结构化数据的系统都会遇到。

## 2. 工具注册与 Executor 的绑定
**用户指令：** 首次尝试让 Agent 执行搜索或文件操作
**现象：** Executor 调用工具时报错，工具未注册或参数不匹配。
**原因：** P0 阶段的 Executor 只是骨架，P1 接入真实工具时涉及工具函数签名、参数校验、错误处理的对齐。
**解决思路：** 统一工具注册方式，确保 `tools/__init__.py` 中导出的工具列表与 Executor 绑定一致。
**备注：** 每新增一个工具都需要确认注册链路是否通畅。

## 3. Perception Agent 输出与 Planner 输入格式不匹配
**用户指令：** 任意用户输入
**现象：** PerceptionAgent 输出的 context 结构（intent、entities、needs_tools）与 Planner prompt 期望的输入格式不完全吻合，导致 Planner 生成的计划质量不稳定。
**原因：** 两个 Agent 的 prompt 是独立编写的，没有严格约定接口契约。
**解决思路：** 在 state.py 中明确 context 的字段规范，两端 prompt 都引用同一规范。
**备注：** Agent 间的"接口契约"是 Multi-Agent 系统的核心设计问题，后续新增 Agent 时同样需要注意。

## 4. StateGraph 条件路由的边界情况
**用户指令：** 执行出错或计划为空时
**现象：** `should_continue` 在 `tool_results` 为空、`plan` 为空等边界情况下行为不确定，可能抛异常或进入意外分支。
**原因：** P0 阶段的 `should_continue` 是最简实现，没有覆盖边界情况。
**解决思路：** 增加空值检查，确保 `tool_results` 和 `plan` 为空时有明确的默认行为。
**备注：** 此问题在 P1→P2 阶段进一步暴露，演变为死循环问题。

## 5. 工具执行结果的格式不统一
**用户指令：** 调用不同工具（搜索 vs 文件操作 vs 代码执行）
**现象：** 各工具返回的结果格式不一致（有的返回字符串，有的返回 dict，有的返回 list），Executor 和 should_continue 难以统一处理。
**原因：** 各工具独立开发，缺乏统一的返回值规范。
**解决思路：** 约定工具返回统一格式，如 `{"tool": "tool_name", "result": ..., "error": None}`。
**备注：** 统一返回格式也有利于 Learner 从执行结果中提取经验。
