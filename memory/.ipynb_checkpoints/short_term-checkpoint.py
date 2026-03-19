from langchain.memory import ConversationBufferWindowMemory
from config import MEMORY_WINDOW_SIZE


class ShortTermMemory:
    def __init__(self):
        self.memory = ConversationBufferWindowMemory(k=MEMORY_WINDOW_SIZE, return_messages=True)

    def add(self, human: str, ai: str):
        self.memory.save_context({"input": human}, {"output": ai})

    def get_messages(self) -> list:
        return self.memory.load_memory_variables({}).get("history", [])

    def clear(self):
        self.memory.clear()
