import subprocess
from langchain_core.tools import tool

MAX_OUTPUT_LEN = 5000


@tool
def execute_python(code: str) -> str:
    """执行 Python 代码并返回输出（stdout + stderr）"""
    try:
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True, text=True, timeout=30,
        )
        output = result.stdout
        if result.stderr:
            output += ("\n--- stderr ---\n" + result.stderr) if output else result.stderr

        if not output.strip():
            output = "(执行完成，无输出)"

        if len(output) > MAX_OUTPUT_LEN:
            output = output[:MAX_OUTPUT_LEN] + f"\n... (输出已截断，共 {len(output)} 字符)"
        return output
    except subprocess.TimeoutExpired:
        return "Error: 执行超时(30s)"
    except Exception as e:
        return f"Error: {e}"
