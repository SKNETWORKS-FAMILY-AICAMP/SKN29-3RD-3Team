from ..chunker.faq_chunker import FAQChunker
import chromadb
from chromadb.utils import embedding_functions
import os
from dotenv import load_dotenv
load_dotenv()

ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-3-small"
)

client = chromadb.PersistentClient(path="preprocessing/chroma_db")

# 기존 collection 삭제 후 재생성
try:
    client.delete_collection("faq_chunks")
except:
    pass
col = client.create_collection(
    name="faq_chunks",
    embedding_function=ef
)

chunker = FAQChunker("../data/2024_주택청약_FAQ.pdf")
chunks = chunker.chunk()
chunker.add_to_chroma(chunks, col)