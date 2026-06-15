from ..chunker.manual_chunker import ManualChunker
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
    client.delete_collection("manual_chunks")
except:
    pass
col = client.create_collection(
    name="manual_chunks",
    embedding_function=ef
)

chunker = ManualChunker("../data/주택공급_업무_매뉴얼.pdf")
chunks = chunker.chunk()
chunker.add_to_chroma(chunks, col)