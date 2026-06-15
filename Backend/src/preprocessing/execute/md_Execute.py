from ..chunker.md_table_chunker import MDTableChunker
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
import chromadb
from dotenv import load_dotenv
load_dotenv()

chunker = MDTableChunker("../data/청약제도안내.md")
docs = chunker.chunk()

embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
db_path = "preprocessing/chroma_db"

# 기존 collection 삭제 후 재생성
client = chromadb.PersistentClient(path=db_path)
try:
    client.delete_collection("guide_chunks")
except Exception:
    pass

vectorstore = Chroma.from_documents(
    documents=docs,
    embedding=embedding_model,
    persist_directory=db_path,
    collection_name="guide_chunks",
)
print(f"[guide_chunks] {len(docs)}개 청크 저장 완료")