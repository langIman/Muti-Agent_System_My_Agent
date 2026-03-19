import os
from langchain_core.tools import tool

MAX_READ_SIZE = 50 * 1024  # 50KB


@tool
def read_file(path: str) -> str:
    """读取本地文件内容"""
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read(MAX_READ_SIZE + 1)
        if len(content) > MAX_READ_SIZE:
            content = content[:MAX_READ_SIZE] + f"\n... (文件过大，已截断至 {MAX_READ_SIZE // 1024}KB)"
        return content
    except FileNotFoundError:
        return f"Error: 文件不存在 - {path}"
    except UnicodeDecodeError:
        return f"Error: 无法读取二进制文件 - {path}"
    except PermissionError:
        return f"Error: 无权限读取 - {path}"
    except Exception as e:
        return f"Error: {e}"


@tool
def write_file(path: str, content: str) -> str:
    """写入内容到本地文件"""
    try:
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"已写入 {path} ({len(content)} 字符)"
    except Exception as e:
        return f"Error: 写入失败 - {e}"


@tool
def list_directory(path: str = ".") -> str:
    """列出目录内容，目录名后有 / 标记"""
    try:
        entries = sorted(os.listdir(path))
        lines = []
        for name in entries:
            full = os.path.join(path, name)
            if os.path.isdir(full):
                lines.append(f"{name}/")
            else:
                size = os.path.getsize(full)
                if size < 1024:
                    lines.append(f"{name}  ({size}B)")
                else:
                    lines.append(f"{name}  ({size // 1024}KB)")
        return "\n".join(lines) if lines else "(空目录)"
    except FileNotFoundError:
        return f"Error: 目录不存在 - {path}"
    except Exception as e:
        return f"Error: {e}"


@tool
def find_file(name: str, search_path: str = ".") -> str:
    """按文件名递归搜索文件，返回所有匹配的文件路径"""
    try:
        matches = []
        skip_dirs = {'.git', '__pycache__', 'node_modules', '.ipynb_checkpoints', 'data', 'venv', '.venv'}
        for root, dirs, files in os.walk(search_path):
            # 限制搜索深度（最多5层）
            depth = root.replace(search_path, '').count(os.sep)
            if depth >= 5:
                dirs.clear()
                continue
            # 跳过无关目录
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
            for f in files:
                if name.lower() in f.lower():
                    rel = os.path.relpath(os.path.join(root, f), search_path)
                    matches.append(rel)
            if len(matches) >= 20:
                break
        if not matches:
            return f"未找到匹配 '{name}' 的文件"
        return "找到以下文件:\n" + "\n".join(f"  {m}" for m in matches)
    except Exception as e:
        return f"Error: {e}"
