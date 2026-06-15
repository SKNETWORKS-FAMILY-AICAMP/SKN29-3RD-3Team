"""
청약홈/마이홈포털 FAQ JSON → Q&A 청크 파서
────────────────────────────────────────────────────────────────
사용법:
    from web_faq_chunker import WebFAQChunker

    chunker = WebFAQChunker(
        myhome_json="myhome_faq_raw.json",
        applyhome_json="applyhome_faq_raw.json",
    )
    chunks = chunker.chunk()

    import chromadb
    client = chromadb.PersistentClient(path="./chroma_db")
    col = client.get_or_create_collection("web_faq_chunks")
    chunker.add_to_chroma(chunks, col)
────────────────────────────────────────────────────────────────
입력 구조:
    myhome_faq_raw.json
        details[].response.detail.{nttSj(질문), nttCn(답변 HTML)}

    applyhome_faq_raw.json
        categories[].response.bbsList[].{NTT_SJ(질문), NTT_CN(답변 HTML), NTCE_SECD_NM(대분류), NTCE_DETAIL_SECD_NM(소분류)}

공통 처리:
    - HTML 태그 제거 (<p>, <br>, &nbsp; 등)
    - source_year="2026" (수집일 기준)
────────────────────────────────────────────────────────────────
"""

import re
import json
import uuid
from dataclasses import dataclass, field


# ── HTML 정리 ───────────────────────────────────────────────────

RE_TAG    = re.compile(r"<[^>]+>")
RE_NBSP   = re.compile(r"&nbsp;")
RE_MIDDOT = re.compile(r"&middot;")
RE_AMP    = re.compile(r"&amp;")
RE_LT     = re.compile(r"&lt;")
RE_GT     = re.compile(r"&gt;")
RE_QUOT   = re.compile(r"&quot;")
RE_BLANKS = re.compile(r"\n{3,}")
RE_SPACES = re.compile(r"[ \t]+")


def clean_html(html: str) -> str:
    """HTML 태그 제거 및 엔티티 변환, 공백 정리"""
    if not html:
        return ""

    text = html

    # <br>, <p> 등을 줄바꿈으로 치환 (태그 제거 전)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</?(strong|b|em|i|span|div|ul|li|ol)[^>]*>", "", text, flags=re.IGNORECASE)

    # 나머지 태그 제거
    text = RE_TAG.sub("", text)

    # 엔티티 변환
    text = RE_NBSP.sub(" ", text)
    text = RE_MIDDOT.sub("·", text)
    text = RE_AMP.sub("&", text)
    text = RE_LT.sub("<", text)
    text = RE_GT.sub(">", text)
    text = RE_QUOT.sub('"', text)

    # 공백 정리
    text = RE_SPACES.sub(" ", text)
    text = RE_BLANKS.sub("\n\n", text)
    lines = [l.strip() for l in text.split("\n")]
    lines = [l for l in lines if l]
    return "\n".join(lines).strip()


@dataclass
class WebFAQChunk:
    page_content: str
    metadata: dict = field(default_factory=dict)


class WebFAQChunker:
    def __init__(
        self,
        myhome_json: str | None = None,
        applyhome_json: str | None = None,
        source_year: str = "2026",
    ):
        self.myhome_json    = myhome_json
        self.applyhome_json = applyhome_json
        self.source_year    = source_year

    def chunk(self) -> list[WebFAQChunk]:
        chunks = []
        if self.myhome_json:
            chunks.extend(self._chunk_myhome(self.myhome_json))
        if self.applyhome_json:
            chunks.extend(self._chunk_applyhome(self.applyhome_json))
        return chunks

    # ── 마이홈포털 ────────────────────────────────────────────────

    def _chunk_myhome(self, path: str) -> list[WebFAQChunk]:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        chunks = []
        for d in data.get("details", []):
            detail = d.get("response", {}).get("detail", {})
            question = (detail.get("nttSj") or "").strip()
            answer_html = detail.get("nttCn") or ""
            answer = clean_html(answer_html)

            if not question or not answer:
                continue

            page_content = f"Q. {question}\n\n{answer}"

            chunks.append(WebFAQChunk(
                page_content=page_content,
                metadata={
                    "source":      data.get("source_name", "마이홈포털"),
                    "source_year": self.source_year,
                    "scope":       data.get("scope", ""),
                    "category":    data.get("target", {}).get("name", ""),
                    "ntt_id":      str(detail.get("nttId", "")),
                    "chunk_level": "qa_pair",
                }
            ))

        return chunks

    # ── 청약홈 ────────────────────────────────────────────────────

    def _chunk_applyhome(self, path: str) -> list[WebFAQChunk]:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        chunks = []
        for cat in data.get("categories", []):
            category_name = cat.get("request", {}).get("category_name", "")
            bbs_list = cat.get("response", {}).get("bbsList", [])

            for item in bbs_list:
                question = (item.get("NTT_SJ") or "").strip()
                answer = clean_html(item.get("NTT_CN") or "")

                if not question or not answer:
                    continue

                page_content = f"Q. {question}\n\n{answer}"

                chunks.append(WebFAQChunk(
                    page_content=page_content,
                    metadata={
                        "source":      data.get("source_name", "청약홈"),
                        "source_year": self.source_year,
                        "scope":       data.get("scope", ""),
                        "category":    category_name,
                        "subcategory": item.get("NTCE_DETAIL_SECD_NM", ""),
                        "bbs_no":      str(item.get("BBS_NO", "")),
                        "bbs_sn":      str(item.get("BBS_SN", "")),
                        "chunk_level": "qa_pair",
                    }
                ))

        return chunks

    # ── ChromaDB 저장 ─────────────────────────────────────────────

    def add_to_chroma(self, chunks: list[WebFAQChunk], collection) -> None:
        if not chunks:
            print("[WebFAQChunker] 저장할 청크가 없습니다.")
            return

        chunks = [c for c in chunks if c.page_content.strip()]

        ids       = [str(uuid.uuid4()) for _ in chunks]
        documents = [c.page_content for c in chunks]
        metadatas = [
            {k: (str(v) if v is not None else "") for k, v in c.metadata.items()}
            for c in chunks
        ]
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"[WebFAQChunker] {len(chunks)}개 청크 저장 완료")


# ── 확인용 출력 ──────────────────────────────────────────────────

def print_chunks(chunks: list[WebFAQChunk], max_content: int = 200) -> None:
    print(f"\n총 {len(chunks)}개 청크\n" + "=" * 75)
    for i, c in enumerate(chunks):
        preview = c.page_content[:max_content].replace("\n", " / ")
        if len(c.page_content) > max_content:
            preview += "..."
        m = c.metadata
        print(
            f"[{i:03d}] {m.get('source',''):<10} "
            f"| {m.get('category','')[:12]:<12} "
            f"| {m.get('subcategory','')[:12]:<12} "
            f"({len(c.page_content)}자)\n"
            f"      {preview}\n"
        )
