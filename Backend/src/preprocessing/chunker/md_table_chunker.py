"""
청약제도안내 마크다운(표 → 자연어 변환본) 청킹 모듈
────────────────────────────────────────────────────────────────
이 청커는 모든 표가 자연어 문장으로 이미 변환된 청약제도안내.md를
대상으로 한다 (convert_tables_to_text.py 로 변환된 버전).
표 블록이 없으므로 표 인식/분할 로직 없이, 헤더 기준 분할 +
1200자 초과 시 문단(빈 줄) 단위 묶음 분할만 수행한다.

사용법:
    from md_table_chunker import MDTableChunker

    chunker = MDTableChunker("청약제도안내.md")
    docs = chunker.chunk()   # langchain Document 리스트

    from langchain_chroma import Chroma
    from langchain_openai import OpenAIEmbeddings
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
        persist_directory="../chroma_db",
        collection_name="guide_chunks",
    )
────────────────────────────────────────────────────────────────
청킹 전략:
    1. H1/H2/H3 헤더 기준 1차 분할 (MarkdownHeaderTextSplitter)
    2. 각 청크가 MAX_CHUNK_SIZE(1200자) 이하면 그대로 사용
    3. 초과하면 문단(빈 줄 기준) 단위로 묶어서 MAX_CHUNK_SIZE 이하로 분할
       → 문장 중간이 잘리지 않고, 문단 경계에서만 나뉨
    4. 모든 청크 앞에 prefix "[Header_1 > Header_2 > Header_3]" 추가

metadata:
    Header_1, Header_2, Header_3  : 마크다운 헤더 계층
    source        : "청약Home 청약제도안내"
    source_year   : "2026"
    chunk_level   : "section"  (표가 없으므로 전부 section)
    doc_title     : H1 (=어느 원본 섹션에서 왔는지)
────────────────────────────────────────────────────────────────
"""

import re
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_core.documents import Document


# ── 설정 ─────────────────────────────────────────────────────────

MAX_CHUNK_SIZE = 1200       # 청크 최대 크기


# ── 문단 단위 분할 ──────────────────────────────────────────────────

def split_into_paragraphs(text: str, max_size: int = MAX_CHUNK_SIZE) -> list[str]:
    """
    빈 줄(\\n\\n) 기준으로 문단 분리. 빈 문단은 제외.
    분리된 문단이 max_size를 넘으면(표 변환 결과처럼 한 줄씩 \\n으로만
    구분된 경우) 줄(\\n) 단위로 한 번 더 쪼갠다.
    """
    paragraphs = re.split(r'\n\s*\n', text)
    result = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if len(p) > max_size and "\n" in p:
            # 줄 단위로 재분할 (표 변환 결과: 한 줄 = 한 문장)
            result.extend(line.strip() for line in p.split("\n") if line.strip())
        else:
            result.append(p)
    return result


def pack_paragraphs(paragraphs: list[str], max_size: int = MAX_CHUNK_SIZE) -> list[str]:
    """
    문단들을 순서대로 묶어 max_size를 넘지 않는 청크들로 분할.
    단일 문단이 max_size를 넘으면 그 문단만 단독 청크로 둠
    (문장을 강제로 자르지 않음).
    """
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for p in paragraphs:
        p_len = len(p)

        if current and current_len + 2 + p_len > max_size:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0

        current.append(p)
        current_len += p_len + (2 if len(current) > 1 else 0)

    if current:
        chunks.append("\n\n".join(current))

    return chunks


# ── prefix 생성 ──────────────────────────────────────────────────

def build_prefix(meta: dict) -> str:
    """
    Header_1/2/3을 조합해 청크 본문 앞에 붙일 컨텍스트 라인 생성.
    예: "[청약제도안내 - 특별공급 > 생애최초 특별공급 > 자격조건]"
    """
    parts = [meta.get(f"Header_{i}") for i in (1, 2, 3)]
    parts = [p.strip() for p in parts if p and p.strip()]
    if not parts:
        return ""
    return "[" + " > ".join(parts) + "]\n\n"


# ── 메인 청커 ────────────────────────────────────────────────────

class MDTableChunker:
    def __init__(
        self,
        md_path: str,
        source_name: str = "청약Home 청약제도안내",
        source_year: str = "2026",
        max_chunk_size: int = MAX_CHUNK_SIZE,
    ):
        self.md_path = md_path
        self.source_name = source_name
        self.source_year = source_year
        self.max_chunk_size = max_chunk_size

    def chunk(self) -> list[Document]:
        with open(self.md_path, encoding="utf-8") as f:
            markdown_document = f.read()

        # 1. H1/H2/H3 기준 1차 분할
        headers_to_split_on = [
            ("#", "Header_1"),
            ("##", "Header_2"),
            ("###", "Header_3"),
        ]
        splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        first_pass = splitter.split_text(markdown_document)

        final_docs: list[Document] = []

        for doc in first_pass:
            content = doc.page_content
            base_meta = dict(doc.metadata)

            # 공통 metadata 주입
            base_meta["source"] = self.source_name
            base_meta["source_year"] = self.source_year
            base_meta["doc_title"] = base_meta.get("Header_1", "")
            base_meta["chunk_level"] = "section"

            # 구분선(---) 제거
            cleaned = re.sub(r'\n+-{3,}\s*$', '', content.strip())
            cleaned = re.sub(r'(?m)^-{3,}\s*$', '', cleaned).strip()

            prefix_len = len(build_prefix(base_meta))
            effective_max = max(self.max_chunk_size - prefix_len, 1)

            if len(cleaned) <= effective_max:
                meta = dict(base_meta)
                final_docs.append(Document(
                    page_content=build_prefix(meta) + cleaned,
                    metadata=meta,
                ))
                continue

            # 2. 1200자(prefix 포함) 초과 -> 문단 단위 분할
            paragraphs = split_into_paragraphs(cleaned, effective_max)
            packed = pack_paragraphs(paragraphs, effective_max)

            for chunk_text in packed:
                chunk_text = chunk_text.strip()
                if not chunk_text:
                    continue
                meta = dict(base_meta)
                final_docs.append(Document(
                    page_content=build_prefix(meta) + chunk_text,
                    metadata=meta,
                ))

        return final_docs


# ── 확인용 출력 ──────────────────────────────────────────────────

def print_chunks(docs: list[Document], max_content: int = 200) -> None:
    print(f"\n총 {len(docs)}개 청크\n" + "=" * 70)
    for i, d in enumerate(docs):
        m = d.metadata
        h1 = (m.get("Header_1") or "")[:20]
        h2 = (m.get("Header_2") or "")[:20]
        h3 = (m.get("Header_3") or "")[:20]
        preview = d.page_content[:max_content].replace("\n", " / ")
        if len(d.page_content) > max_content:
            preview += "..."
        print(
            f"[{i:03d}] {m.get('chunk_level',''):<8} "
            f"{h1:<20} | {h2:<20} | {h3:<20} "
            f"({len(d.page_content)}자)\n"
            f"      {preview}\n"
        )


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "청약제도안내.md"
    chunker = MDTableChunker(path)
    docs = chunker.chunk()
    print_chunks(docs)
