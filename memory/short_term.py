from collections import deque
from config import MEMORY_WINDOW_SIZE


class ShortTermMemory:
    def __init__(self):
        self._buffer = deque(maxlen=MEMORY_WINDOW_SIZE)

    def add(self, human: str, ai: str):
        self._buffer.append({"human": human, "ai": ai})
    def get_messages(self) -> list:
        return list(self._buffer)

    def clear(self):
        self._buffer.clear()
