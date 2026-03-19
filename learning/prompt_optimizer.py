import json
import os


class PromptOptimizer:
    """基于反馈优化 Agent 的 system prompt"""

    def __init__(self, path: str = "data/prompt_patches.json"):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.patches = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.patches, f, ensure_ascii=False, indent=2)

    def add_patch(self, agent_name: str, patch: str):
        self.patches.setdefault(agent_name, []).append(patch)
        self._save()

    def get_patches(self, agent_name: str) -> list:
        return self.patches.get(agent_name, [])
