import json
import os


class StrategyStore:
    """存储和检索成功策略"""

    def __init__(self, path: str = "data/strategies.json"):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.strategies = self._load()

    def _load(self) -> list:
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.strategies, f, ensure_ascii=False, indent=2)

    def add(self, strategy: dict):
        self.strategies.append(strategy)
        self._save()

    def search(self, keyword: str) -> list:
        return [s for s in self.strategies if keyword.lower() in json.dumps(s, ensure_ascii=False).lower()]
