import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "data", "chroma")
MEMORY_WINDOW_SIZE = 20
RETRIEVER_TOP_K = 5
EPISODIC_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "episodic.db")
EPISODIC_SEARCH_LIMIT = 5
STRATEGY_STORE_PATH = os.path.join(os.path.dirname(__file__), "data", "strategies.json")
PROMPT_PATCHES_PATH = os.path.join(os.path.dirname(__file__), "data", "prompt_patches.json")
