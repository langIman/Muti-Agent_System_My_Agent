from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from config import CHROMA_DIR, RETRIEVER_TOP_K, OPENAI_API_KEY, OPENAI_BASE_URL, RELEVANCE_THRESHOLD


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

    def retrieve(self, query: str) -> str:
        results = self.vectorstore.similarity_search_with_relevance_scores(
            query, k=RETRIEVER_TOP_K
        )
        # 只保留相关性高于阈值的结果
        filtered = [(doc, score) for doc, score in results if score >= RELEVANCE_THRESHOLD]
        return "\n".join(doc.page_content for doc, _ in filtered)

    def store(self, text: str, metadata: dict = None):
        self.vectorstore.add_texts([text], metadatas=[metadata or {}])
