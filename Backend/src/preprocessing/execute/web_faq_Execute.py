from ..chunker.web_faq_chunker import WebFAQChunker
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

try:
    client.delete_collection("web_faq_chunks")
except:
    pass
col = client.create_collection(
    name="web_faq_chunks",
    embedding_function=ef
)

chunker = WebFAQChunker(
    myhome_json="../data/myhome_faq_raw.json",
    applyhome_json="../data/applyhome_faq_raw.json",
)
chunks = chunker.chunk()
chunker.add_to_chroma(chunks, col)