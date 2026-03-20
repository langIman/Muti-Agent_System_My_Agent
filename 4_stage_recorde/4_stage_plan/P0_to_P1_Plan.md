# P0 → P1 实施计划：接入真实工具，Executor 能完成实际任务

## 目标
让 Executor 从骨架变为可用，接入搜索、文件操作、代码执行等真实工具，完成实际任务。

## 现状分析（P0 完成后）
- StateGraph 流转骨架已搭建：perceive → plan → execute → learn
- 五大 Agent 基类和子类已定义，但 Executor 没有可用工具
- `tools/` 目录下文件为空或占位

## 实施步骤

### 步骤 1：实现搜索工具 (tools/search.py)
实现 `web_search` 函数，接入搜索 API（如 DuckDuckGo），返回搜索结果摘要。

### 步骤 2：实现文件操作工具 (tools/file_ops.py)
实现 `read_file`、`write_file`、`list_directory`、`find_file` 四个函数，覆盖文件读写和目录浏览。

### 步骤 3：实现代码执行工具 (tools/code_exec.py)
实现 `execute_python`，在沙箱中执行 Python 代码并捕获输出和异常。

### 步骤 4：实现 API 调用工具 (tools/api_caller.py)
实现 `api_call`，支持 GET/POST 请求，返回响应内容。

### 步骤 5：实现终止工具 (reply_user / task_complete)
实现 `reply_user` 和 `task_complete`，用于向用户回复和标记任务结束，配合 `should_continue` 的路由逻辑。

### 步骤 6：Executor 绑定工具
在 `agents/executor.py` 中注册所有工具，让 LLM 能通过 tool_calling 机制调用它们。统一工具返回格式为 `{"tool": "tool_name", "result": ..., "error": None}`。

### 步骤 7：工具注册与导出 (tools/__init__.py)
在 `tools/__init__.py` 中统一导出工具列表，供 Executor 和 Planner 引用。

### 步骤 8：Planner prompt 更新
在 Planner 的 system_prompt 中列出所有可用工具及其参数说明，让 Planner 能生成合理的工具调用计划。

## 预期产出
- Executor 能调用搜索、文件、代码执行、API 等工具完成实际任务
- `should_continue` 能根据 `reply_user` / `task_complete` 正确终止流程
