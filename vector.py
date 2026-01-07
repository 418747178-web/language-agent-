from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import CharacterTextSplitter

class VectorEngine:
    def __init__(self, collection_name="lang_learning_data"):
        self.embeddings = OpenAIEmbeddings()
        self.db = None
        self.collection_name = collection_name

    def add_texts(self, texts: list):
        """将学习资料存入向量库"""
        # 1. 切分长文本
        text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        docs = text_splitter.create_documents(texts)
        # 2. 向量化并存储
        self.db = Chroma.from_documents(
            docs, self.embeddings, persist_directory="./chroma_db"
        )

    def query_similar_context(self, word: str):
        """检索与生词相关的背景例句"""
        if not self.db:
            self.db = Chroma(persist_directory="./chroma_db", embedding_function=self.embeddings)
        results = self.db.similarity_search(word, k=2)
        return [doc.page_content for doc in results]