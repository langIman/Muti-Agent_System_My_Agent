import requests
from langchain_core.tools import tool


@tool
def api_call(url: str, method: str = "GET", body: str = "") -> str:
    """调用外部 HTTP API"""
    try:
        resp = requests.request(method, url, data=body, timeout=15)
        return resp.text[:2000]
    except Exception as e:
        return f"Error: {e}"
