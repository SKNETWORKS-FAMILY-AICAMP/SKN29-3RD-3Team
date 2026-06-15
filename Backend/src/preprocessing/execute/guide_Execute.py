from ..chunker.lh_guide_chunker import LHGuideChunker
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
    client.delete_collection("lh_guide_chunks")
except:
    pass
col = client.create_collection(
    name="lh_guide_chunks",
    embedding_function=ef
)

chunker = LHGuideChunker(
    procedure_pdf      = "../data/guide_procedure.pdf",
    general_supply_pdf = "../data/guide_general.pdf",
    special_supply_pdf = "../data/guide_special.pdf",
    transfer_limit_pdf = "../data/guide_transfer.pdf",
)
chunks = chunker.chunk()
chunker.add_to_chroma(chunks, col)
