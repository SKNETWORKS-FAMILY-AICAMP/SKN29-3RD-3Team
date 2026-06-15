"""
청약 법령 RAG 청킹 모듈
────────────────────────────────────────────────────────────────
사용법:
    from law_chunker import LawChunker

    with open("law.txt", encoding="utf-8") as f:
        text = f.read()

    chunker = LawChunker(law_name="주택공급에 관한 규칙")
    chunks = chunker.chunk(text)           # 부칙 자동 제거
    chunker.add_to_chroma(chunks, col)

    from law_chunker import print_chunks
    print_chunks(chunks)
────────────────────────────────────────────────────────────────
청킹 전략:
  1. 부칙 자동 제거
  2. 장(章) 정보를 metadata에 추가
  3. 조 단위로 분리 → 길이 기준으로 항→호→목 계층 분리
  4. 짧은 항/호는 병합 (누적 길이 임계값 기준)
  5. 호/목 청크에 상위 문맥(조제목 + 항 도입문) prefix 포함
────────────────────────────────────────────────────────────────
"""

import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

# ── 임계값 ──────────────────────────────────────────────────────
# 한국어 1글자 ≈ 0.6~0.8 토큰
# 사용하는 embedding 모델 토큰 한도에 맞게 조정할 것
# text-embedding-3-small 등 8191토큰 모델이면 값을 훨씬 크게 잡아도 됨
ARTICLE_THRESHOLD   = 1500
PARAGRAPH_THRESHOLD = 700
ITEM_THRESHOLD      = 500

# ── 정규식 ──────────────────────────────────────────────────────

# 장: 줄 시작에서만
RE_CHAPTER = re.compile(r"(?m)^(제\d+장[^\n]+)")

# 조: 줄 시작에서만 — 본문 내 "제3조제2항" 같은 참조 표현과 구별
RE_ARTICLE = re.compile(
    r"(?m)^(제\d+조(?:의\d+)?)"
    r"(?:\(([^)]+)\))?"
    r"(?=[ \t①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳\n]|$)"
)

# 항: 줄 시작에서만
RE_PARAGRAPH = re.compile(
    r"(?m)^[ \t]*([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳])"
)

# 호: 줄 시작에서 "숫자."
RE_ITEM = re.compile(r"(?m)^[ \t]*(\d+(?:의\d+)?)\. ")

# 목: 줄 시작에서 "한글자."
RE_SUBITEM = re.compile(r"(?m)^[ \t]*([가-힣])\. ")

# 개정·신설·삭제 이력
RE_REVISION = re.compile(r"<[^>]+>")

# 부칙
RE_EPILOGUE = re.compile(r"(?m)^부칙\b")

PARA_CHAR_TO_NUM = {
    c: i + 1 for i, c in enumerate("①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳")
}
SUBITEM_CHAR_TO_NUM = {
    c: i + 1 for i, c in enumerate("가나다라마바사아자차카타파하")
}


# ── 데이터 클래스 ────────────────────────────────────────────────

@dataclass
class LawChunk:
    page_content: str
    metadata: dict = field(default_factory=dict)


# ── 전처리 ──────────────────────────────────────────────────────

def preprocess(text: str) -> str:
    """
    1) 부칙 이후 제거
    2) 조제목 뒤에 붙은 항기호 줄바꿈 분리
       "제4조(제목) ①" → "제4조(제목)\n①"
    3) 개정 이력 제거
    4) 공백/줄바꿈 정리
    """
    # 부칙 제거
    m = RE_EPILOGUE.search(text)
    if m:
        text = text[:m.start()]

    # 개정 이력 제거
    text = RE_REVISION.sub("", text)

    # 조제목 + 항기호 분리
    text = re.sub(
        r"(제\d+조(?:의\d+)?(?:\([^)]+\))?)\s*"
        r"([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳])",
        r"\1\n\2",
        text,
    )

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_chapter_map(text: str) -> dict[str, str]:
    """
    조번호 → 장 이름 매핑 반환.
    예: {"1": "제1장 총칙", "2": "제1장 총칙", "5": "제2장 입주자저축", ...}
    """
    events = []
    for m in RE_CHAPTER.finditer(text):
        events.append((m.start(), "chapter", m.group(1).strip()))
    for m in RE_ARTICLE.finditer(text):
        num = _parse_article_number(m.group(1))
        events.append((m.start(), "article", num))
    events.sort()

    chapter_map = {}
    current_chapter = ""
    for _, kind, label in events:
        if kind == "chapter":
            current_chapter = label
        elif kind == "article":
            chapter_map[label] = current_chapter
    return chapter_map


# ── 유틸리티 ────────────────────────────────────────────────────

def split_by_line_pattern(text: str, pattern: re.Pattern) -> list[tuple[str, str]]:
    matches = list(pattern.finditer(text))
    if not matches:
        return []
    parts = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        parts.append((m.group(1), text[start:end].strip()))
    return parts


def split_articles(text: str) -> list[tuple[str, Optional[str], str]]:
    matches = list(RE_ARTICLE.finditer(text))
    if not matches:
        return []
    articles = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        articles.append((m.group(1), m.group(2), text[start:end].strip()))
    return articles


def _parse_article_number(article_num: str) -> str:
    m = re.match(r"제(\d+)조(?:의(\d+))?", article_num)
    if not m:
        return article_num
    return f"{m.group(1)}-{m.group(2)}" if m.group(2) else m.group(1)


def _normalize_item(label: str) -> str:
    return label.replace("의", "-")


# ── 청킹 ────────────────────────────────────────────────────────

class LawChunker:
    def __init__(self, law_name: str = ""):
        self.law_name = law_name

    def _meta(
        self,
        article_num: str,
        article_title: Optional[str],
        chapter: str = "",
        paragraph: Optional[int] = None,
        item: Optional[str] = None,
        item_sub: Optional[str] = None,
        chunk_level: str = "article",
    ) -> dict:
        return {
            "law":           self.law_name,
            "chapter":       chapter,
            "article":       _parse_article_number(article_num),
            "article_title": article_title or "",
            "paragraph":     str(paragraph) if paragraph else "",
            "item":          item or "",
            "item_sub":      str(item_sub) if item_sub else "",
            "chunk_level":   chunk_level,
        }

    def _art_prefix(self, article_num: str, article_title: Optional[str]) -> str:
        return f"{article_num}({article_title})" if article_title else article_num

    # ── 목 ──────────────────────────────────────────────────────

    def _chunk_subitems(self, text, article_num, article_title, chapter, para_num, item_label, ctx):
        parts = split_by_line_pattern(text, RE_SUBITEM)
        if not parts:
            return [LawChunk(
                page_content=f"{ctx}\n{text}".strip(),
                metadata=self._meta(article_num, article_title, chapter, para_num, item_label, chunk_level="item"),
            )]
        chunks, buf, keys = [], [], []
        def flush():
            if not buf: return
            sub = str(SUBITEM_CHAR_TO_NUM.get(keys[0], keys[0]))
            chunks.append(LawChunk(
                page_content=f"{ctx}\n" + "\n".join(buf),
                metadata=self._meta(article_num, article_title, chapter, para_num, item_label, sub, "subitem"),
            ))
        for char, block in parts:
            if sum(len(l) for l in buf) + len(block) <= ITEM_THRESHOLD:
                buf.append(block); keys.append(char)
            else:
                flush(); buf, keys = [block], [char]
        flush()
        return chunks

    # ── 호 ──────────────────────────────────────────────────────

    def _chunk_items(self, text, article_num, article_title, chapter, para_num, para_intro):
        parts = split_by_line_pattern(text, RE_ITEM)
        art_prefix = self._art_prefix(article_num, article_title)
        if not parts:
            return [LawChunk(
                page_content=f"{art_prefix}\n{text}".strip(),
                metadata=self._meta(article_num, article_title, chapter, para_num, chunk_level="paragraph"),
            )]
        ctx = f"{art_prefix}\n{para_intro}".strip()
        chunks, buf, keys = [], [], []
        def flush():
            if not buf: return
            label = _normalize_item(keys[0])
            chunks.append(LawChunk(
                page_content=f"{ctx}\n" + "\n".join(buf),
                metadata=self._meta(article_num, article_title, chapter, para_num, label, chunk_level="item"),
            ))
        for item_num, item_text in parts:
            if len(item_text) > ITEM_THRESHOLD:
                flush(); buf, keys = [], []
                chunks.extend(self._chunk_subitems(
                    item_text, article_num, article_title, chapter,
                    para_num, _normalize_item(item_num), ctx,
                ))
            elif sum(len(l) for l in buf) + len(item_text) <= PARAGRAPH_THRESHOLD:
                buf.append(item_text); keys.append(item_num)
            else:
                flush(); buf, keys = [item_text], [item_num]
        flush()
        return chunks

    # ── 항 ──────────────────────────────────────────────────────

    def _chunk_paragraphs(self, article_body, article_num, article_title, chapter):
        para_parts = split_by_line_pattern(article_body, RE_PARAGRAPH)
        art_prefix = self._art_prefix(article_num, article_title)

        # 항 없는 조 → 호로 바로
        if not para_parts:
            m = RE_ITEM.search(article_body)
            intro = article_body[:m.start()].strip() if m else article_body.split("\n")[0].strip()
            return self._chunk_items(article_body, article_num, article_title, chapter, None, intro)

        chunks, buf, keys = [], [], []
        def flush():
            if not buf: return
            para_num = PARA_CHAR_TO_NUM.get(keys[0], 1)
            chunks.append(LawChunk(
                page_content=f"{art_prefix}\n" + "\n".join(buf),
                metadata=self._meta(article_num, article_title, chapter, para_num, chunk_level="paragraph"),
            ))
        for para_char, para_text in para_parts:
            para_num = PARA_CHAR_TO_NUM.get(para_char, 1)
            if len(para_text) > PARAGRAPH_THRESHOLD:
                flush(); buf, keys = [], []
                m = RE_ITEM.search(para_text)
                intro = para_text[:m.start()].strip() if m else para_text.split("\n")[0].strip()
                chunks.extend(self._chunk_items(
                    para_text, article_num, article_title, chapter, para_num, intro
                ))
            elif sum(len(l) for l in buf) + len(para_text) <= PARAGRAPH_THRESHOLD:
                buf.append(para_text); keys.append(para_char)
            else:
                flush(); buf, keys = [para_text], [para_char]
        flush()
        return chunks

    # ── 조 ──────────────────────────────────────────────────────

    def _process_article(self, article_num, article_title, article_body, chapter):
        if len(article_body) <= ARTICLE_THRESHOLD:
            return [LawChunk(
                page_content=article_body,
                metadata=self._meta(article_num, article_title, chapter, chunk_level="article"),
            )]
        return self._chunk_paragraphs(article_body, article_num, article_title, chapter)

    # ── 진입점 ──────────────────────────────────────────────────

    def chunk(self, text: str) -> list[LawChunk]:
        """법령 전체 텍스트 → LawChunk 리스트 (부칙 자동 제거)"""
        text = preprocess(text)
        chapter_map = extract_chapter_map(text)
        articles = split_articles(text)

        if not articles:
            return [LawChunk(page_content=text, metadata={"law": self.law_name, "chunk_level": "full"})]

        chunks = []
        for article_num, article_title, body in articles:
            body = preprocess(body)
            article_key = _parse_article_number(article_num)
            chapter = chapter_map.get(article_key, "")
            chunks.extend(self._process_article(article_num, article_title, body, chapter))
        return chunks

    # ── ChromaDB ─────────────────────────────────────────────────

    def add_to_chroma(self, chunks: list[LawChunk], collection) -> None:
        """
        예시:
            import chromadb
            client = chromadb.PersistentClient(path="./chroma_db")
            col = client.get_or_create_collection("law_chunks")
            chunker.add_to_chroma(chunks, col)
        """
        if not chunks:
            print("[LawChunker] 저장할 청크가 없습니다.")
            return
        ids       = [str(uuid.uuid4()) for _ in chunks]
        documents = [c.page_content for c in chunks]
        metadatas = [
            {k: (v if v is not None else "") for k, v in c.metadata.items()}
            for c in chunks
        ]
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"[LawChunker] {len(chunks)}개 청크 저장 완료")


# ── 확인용 출력 ──────────────────────────────────────────────────

def print_chunks(chunks: list[LawChunk], max_content: int = 150) -> None:
    print(f"\n총 {len(chunks)}개 청크\n" + "=" * 70)
    for i, c in enumerate(chunks):
        preview = c.page_content[:max_content].replace("\n", " / ")
        if len(c.page_content) > max_content:
            preview += "..."
        m = c.metadata
        print(
            f"[{i:03d}] level={m.get('chunk_level'):<10} "
            f"장={m.get('chapter') or '-':<20} "
            f"조={m.get('article'):<6} "
            f"항={m.get('paragraph') or '-':<4} "
            f"호={m.get('item') or '-':<6} "
            f"({len(c.page_content)}자)\n"
            f"      {preview}\n"
        )
