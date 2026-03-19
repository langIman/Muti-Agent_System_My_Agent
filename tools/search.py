from langchain_core.tools import tool


@tool
def web_search(query: str) -> str:
    """搜索互联网获取信息，返回相关网页的标题、摘要和链接"""
    try:
        from ddgs import DDGS

        results = DDGS().text(query, max_results=5)
        if not results:
            return f"未找到与 '{query}' 相关的结果"

        output = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "无标题")
            body = r.get("body", "")
            href = r.get("href", "")
            output.append(f"{i}. {title}\n   {body}\n   链接: {href}")
        return "\n\n".join(output)
    except Exception as e:
        return f"搜索出错: {e}"
