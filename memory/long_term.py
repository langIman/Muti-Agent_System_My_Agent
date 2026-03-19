from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from config import CHROMA_DIR, RETRIEVER_TOP_K, OPENAI_API_KEY, OPENAI_BASE_URL


class LongTermMemory:
    def __init__(self):
        self.vectorstore = Chroma(
            collection_name="long_term",
            embedding_function=OpenAIEmbeddings(
                model="text-embedding-v3",
                api_key=OPENAI_API_KEY,
                base_url=OPENAI_BASE_URL,
                check_embedding_ctx_length=False,
            ),
            persist_directory=CHROMA_DIR,
        )
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": RETRIEVER_TOP_K})

    def retrieve(self, query: str) -> str:
        docs = self.retriever.invoke(query)
        return "\n".join(d.page_content for d in docs)

    def store(self, text: str, metadata: dict = None):
        self.vectorstore.add_texts([text], metadatas=[metadata or {}])
