# P2 → P3 阶段遇到的问题

## 1. AIMessage/ToolMessage 消息序列污染（400 错误）
**用户指令：** 接入 Learner 反馈闭环后首次运行
**现象：** LLM API 返回 400 错误，任务无法执行。
**原因：** Planner、Learner、MemoryAgent 在返回时带上了自身的 AIMessage，这些消息通过 `add_messages` 被追加到 `state["messages"]` 中。Executor 执行时，消息历史里出现了"带 tool_calls 的 AIMessage 后面没有紧跟 ToolMessage"的非法序列，OpenAI/Anthropic API 强制校验该顺序，因此报 400。
**解决思路：** 不调用工具的 Agent（Planner、Learner、MemoryAgent）统一返回 `"messages": []`，不往消息历史中写入任何内容。只有 Perception 和 Executor 才需要往 messages 里写消息。
**备注：** 这是 LangGraph 多 Agent 架构中最容易踩的坑。根本规则：`add_messages` 会累积所有节点的返回消息，任何带 tool_calls 的 AIMessage 必须在同一批消息里紧跟对应的 ToolMessage，否则下一次 LLM 调用就会因非法序列报错。

## 2. Executor 跨步骤无法传递工具结果
**用户指令：** "搜索伊朗最新新闻，写入文件"
**现象：** Executor 执行 write_file 步骤时，无法获取上一步 web_search 的结果，写入内容为空或乱造。
**原因：** Executor 为了避免消息序列污染，不再使用 `state["messages"]`，但也因此丢失了前序步骤的执行结果。
**解决思路：** 引入独立的 `tool_results` 列表专门存储工具执行结果。Executor 每次执行前，把 `tool_results` 中前序步骤的结果拼成摘要注入到 `exec_messages` 中，作为上下文传给 LLM，从而实现跨步骤数据传递，同时不污染主消息历史。
**备注：** 这是一个架构上的权衡——用独立的 `tool_results` 作为步骤间通信管道，与 `messages` 的对话历史完全隔离。

## 3. Planner 在任务已完成时仍重复规划
**用户指令：** 文件写入成功后，Agent 继续生成新计划并再次尝试写入。
**现象：** 任务实际已完成，但 `should_continue` 判断为 `"replan"`，Planner 再次规划导致重复操作。
**原因：** Planner 的 prompt 没有明确要求在任务真正完成后生成 `task_complete` 步骤，LLM 倾向于继续生成"改进"计划。
**解决思路：** 在 Planner prompt 中加入强制规则："如果确认用户原始指令已完全执行成功，必须生成 1 步 `task_complete` 计划结束任务"，并加粗标注为绝对规则；同时引入 `MAX_REPLAN=3` 上限兜底，防止极端情况下的无限循环。
**备注：** 与 P2 阶段的死循环问题类似，但触发场景不同——P2 是计划没有终止工具，P3 是任务已完成但 LLM 不知道该停止。

## 4. Learner 提取经验时产生幻觉
**用户指令：** 多轮任务后观察 Learner 输出
**现象：** `lesson_list` 中出现了具体的操作步骤或伪代码，而不是总结性经验，如 `{"step": 1, "action": "web_search", ...}`。
**原因：** Learner 的 LLM 在总结时混淆了"复盘经验"和"生成计划"两种任务，把下一步的执行建议当成经验写入。
**解决思路：** 在 Learner prompt 中明确禁止输出操作步骤；在代码层面增加过滤逻辑，检测到 `{"step": ...}` 格式的 dict 直接丢弃并打印警告。
**备注：** 提示词约束 + 代码兜底的双重防御是处理 LLM 幻觉的标准做法。

## 5. main.py 注释错误 & 消息格式不一致
**现象：** `# 提取 AI 回复并写入短期记忆` 注释误导，该段代码实际只负责提取并打印，写入短期记忆是后续第 71 行的操作；另外 `session_state["messages"].append(("user", user_input))` 用元组格式追加消息，与 `AgentState` 期望的 `HumanMessage` 对象不一致。
**原因：** 代码迭代过程中注释未同步更新；消息格式使用了 LangGraph 兼容但不规范的元组写法。
**解决思路：** 修正注释；将消息格式统一改为 `HumanMessage(content=user_input)`；同时为兜底输出逻辑添加 `messages` 为空时的保护，避免 `IndexError`。
**备注：** 属于代码规范问题，不影响核心功能，但统一格式有助于后续调试。
