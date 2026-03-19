import sqlite3
import json
import os
from datetime import datetime


class EpisodicMemory:
    def __init__(self, db_path: str = "data/episodic.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS episodes ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "task TEXT, result TEXT, lessons TEXT, timestamp TEXT)"
        )
        self.conn.commit()

    def add(self, task: str, result: str, lessons: list):
        self.conn.execute(
            "INSERT INTO episodes (task, result, lessons, timestamp) VALUES (?,?,?,?)",
            (task, result, json.dumps(lessons, ensure_ascii=False), datetime.now().isoformat()),
        )
        self.conn.commit()

    def search(self, keyword: str, limit: int = 5) -> list[dict]:
        rows = self.conn.execute(
            "SELECT task, result, lessons, timestamp FROM episodes "
            "WHERE task LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{keyword}%", limit),
        ).fetchall()
        return [{"task": r[0], "result": r[1], "lessons": json.loads(r[2]), "ts": r[3]} for r in rows]
