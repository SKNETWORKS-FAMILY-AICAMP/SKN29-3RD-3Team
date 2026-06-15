from ..chunker.law_chunker import LawChunker, print_chunks
import chromadb
import re
from chromadb.utils import embedding_functions
import os
from dotenv import load_dotenv
load_dotenv()

# HWPML(XML) → 텍스트 추출
HWP_PATH = r"..\data\주택공급에 관한 규칙(국토교통부령)(제01531호)(20251031) (1).hwp"

with open(HWP_PATH, encoding="utf-8") as f:
    content = f.read()

chars = re.findall(r'<CHAR[^>]*>([^<]+)</CHAR>', content)
text = "\n".join(chars)
text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
text = re.sub(r'[ \t]+', ' ', text)
text = re.sub(r'\n{3,}', '\n\n', text)

chunker = LawChunker(law_name="주택공급에 관한 규칙")
chunks = chunker.chunk(text)
print_chunks(chunks)  # 확인용

# OpenAI embedding 지정
ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-3-small"
)

client = chromadb.PersistentClient(path="preprocessing/chroma_db")
col = client.get_or_create_collection(
    name="law_chunks",
    embedding_function=ef
)
chunker.add_to_chroma(chunks, col)