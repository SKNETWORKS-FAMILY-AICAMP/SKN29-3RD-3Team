"""
2024 주택청약 FAQ PDF → Q&A 청크 파서 (v2, pypdf 기반)
────────────────────────────────────────────────────────────────
pypdf로 추출한 텍스트는 Q번호가 "숫자 + 공백 + 질문텍스트"가
한 줄에 붙어서 나옴 (pdftotext와 다른 패턴).

    예: "1 경기도 과천시에서 공급되는 주택의 해당 주택건설지역의 범위는?"
        "8 해외체류 기간 산정 방법"

문서 구조:
    - page 0~1   : 표지/안내문
    - page 2~31  : 목차 (로마숫자 페이지번호, "Q1.", "Q50." 형태 + 점선)
    - page 32~272: 본문
        라인 패턴:
          "Ⅰ. 청약자격(공통)"      ← 챕터 헤더 (페이지 상단 반복)
          "3"                       ← 페이지 번호 (단독 숫자줄, Q번호 아님)
          "청약신청지역1"            ← 소제목+번호 (무시)
          "가. 주요내용"            ← 중분류(섹션)
          "1 경기도 과천시...?"     ← Q번호+질문 (한 줄)
          "해당 주택건설지역..."     ← 답변 (여러 줄)
────────────────────────────────────────────────────────────────
사용법:
    from faq_chunker import FAQChunker, print_chunks

    chunker = FAQChunker("path/to/FAQ.pdf")
    chunks = chunker.chunk()
    print_chunks(chunks)

    import chromadb
    client = chromadb.PersistentClient(path="./chroma_db")
    col = client.get_or_create_collection("faq_chunks")
    chunker.add_to_chroma(chunks, col)
────────────────────────────────────────────────────────────────
"""

import re
import uuid
from dataclasses import dataclass, field


# ── 패턴 ────────────────────────────────────────────────────────

RE_FF        = re.compile(r"\f")
RE_DOTS      = re.compile(r"[·ㆍ]{3,}|\.{4,}")
RE_CHAPTER   = re.compile(r"^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩIVX]+\.\s*.+$")
RE_ROMAN_ONLY = re.compile(r"^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+$")  # 로마숫자 단독줄 (챕터명과 분리된 경우)
RE_SEC_KOR   = re.compile(r"^[가나다라마바사아자차카타파하]\.\s+.+$")
RE_PAGE_NUM  = re.compile(r"^\d{1,3}$")            # 페이지번호 단독 줄
RE_INLINE_Q  = re.compile(r"^(\d{1,3})\s+(.+)$")    # "1 질문...?" 형태
RE_LAW_ITEM  = re.compile(r"^\d+\.\s+.+")           # "3. 제1호..." 법령조항
RE_HEADER    = re.compile(
    r"^(2024\s*주택청약\s*FAQ|Apartment Application FAQ.*|www\.molit\.go\.kr)$"
)

BODY_START_PAGE = 32   # 0-indexed, 본문 시작 페이지 (목차는 그 이전)


@dataclass
class FAQChunk:
    page_content: str
    metadata: dict = field(default_factory=dict)


def extract_text(pdf_path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    return "\f".join(page.extract_text() or "" for page in reader.pages)


def is_toc_page(page_text: str) -> bool:
    """목차 페이지 판별: 점선(목차 leader) 패턴이 다수 존재"""
    return sum(1 for l in page_text.split("\n") if RE_DOTS.search(l)) >= 3


class FAQChunker:
    def __init__(self, pdf_path: str, source_name: str = "2024 주택청약 FAQ", source_year: str = "2024"):
        self.pdf_path = pdf_path
        self.source_name = source_name
        self.source_year = source_year

    def chunk(self) -> list[FAQChunk]:
        raw = extract_text(self.pdf_path)
        lines = self._clean_lines(raw)
        return self._parse(lines)

    # ── 전처리 ──────────────────────────────────────────────────

    def _clean_lines(self, raw: str) -> list[str]:
        """
        페이지별로 분리 → 목차 페이지 제외 → 본문 시작 페이지(BODY_START_PAGE) 이전 제외
        → 페이지 번호 단독 줄 / 머리말 / 점선 제거
        → "챕터명\n로마숫자" 두 줄로 나뉜 챕터 헤더를 "로마숫자. 챕터명" 형태로 정규화
        """
        pages = RE_FF.split(raw)
        raw_lines: list[str] = []

        for page_idx, page in enumerate(pages):
            if page_idx < BODY_START_PAGE:
                continue
            if is_toc_page(page):
                continue

            for line in page.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if RE_HEADER.match(line):
                    continue
                if RE_DOTS.search(line):
                    continue
                if RE_PAGE_NUM.match(line):
                    # 페이지 번호 단독 줄 (예: "3", "49") → 제거
                    continue
                raw_lines.append(line)

        # "챕터명" 다음 줄이 로마숫자 단독줄("Ⅶ")이면 "Ⅶ. 챕터명"으로 합침
        lines: list[str] = []
        i = 0
        while i < len(raw_lines):
            cur = raw_lines[i]
            nxt = raw_lines[i + 1] if i + 1 < len(raw_lines) else ""
            if RE_ROMAN_ONLY.match(nxt) and not RE_CHAPTER.match(cur) and not RE_INLINE_Q.match(cur):
                lines.append(f"{nxt}. {cur}")
                i += 2
                continue
            lines.append(cur)
            i += 1

        return lines

    # ── Q번호 판별 ──────────────────────────────────────────────

    def _is_real_q(self, lines: list[str], i: int) -> tuple[bool, int, str] | None:
        """
        i번째 줄이 "Q번호 + 질문" 형태인지 판별.
        성공 시 (True, q_num, question_text) 반환, 아니면 None.

        조건:
          1. "숫자 + 공백 + 텍스트" 형태 (RE_INLINE_Q)
          2. 법령조항("3. 제1호...")이 아닐 것 (RE_LAW_ITEM)
          3. 챕터/섹션 헤더가 아닐 것
          4. 텍스트가 충분히 길 것 (너무 짧은 건 노이즈)
        """
        line = lines[i]
        m = RE_INLINE_Q.match(line)
        if not m:
            return None

        num_str, rest = m.groups()

        if RE_LAW_ITEM.match(line):
            return None
        if RE_CHAPTER.match(line) or RE_SEC_KOR.match(line):
            return None
        if len(rest) < 5:
            return None

        return True, int(num_str), rest

    def _parse(self, lines: list[str]) -> list[FAQChunk]:
        # 1. Q번호 후보 위치 수집
        candidates: list[tuple[int, int, str]] = []
        for i in range(len(lines)):
            result = self._is_real_q(lines, i)
            if result:
                _, q_num, question = result
                candidates.append((i, q_num, question))

        # 2. 순증가 시퀀스 필터링
        q_positions = self._filter_sequential(candidates)

        # 3. 챕터/섹션 맵 구축
        chapter_map = self._build_chapter_map(lines)

        # 4. 청크 생성
        chunks = []
        for idx, (pos, q_num, question) in enumerate(q_positions):
            end = q_positions[idx + 1][0] if idx + 1 < len(q_positions) else len(lines)
            chapter, section = chapter_map.get(pos, ("", ""))
            chunk = self._build_chunk(lines, pos, end, q_num, question, chapter, section)
            if chunk:
                chunks.append(chunk)

        return chunks

    def _filter_sequential(
        self, candidates: list[tuple[int, int, str]]
    ) -> list[tuple[int, int, str]]:
        """
        Q번호가 순증가하는 시퀀스만 유효로 인정.
        본문은 1부터 480까지 거의 연속으로 증가하므로,
        '이전 번호보다 크거나 같은' 경우만 채택하고 중복은 마지막 것을 사용.
        """
        if not candidates:
            return []

        valid: list[tuple[int, int, str]] = []
        prev_q = 0

        for pos, q_num, question in candidates:
            # 이전 번호보다 크면 정상 흐름
            if q_num > prev_q:
                # 너무 큰 점프(예: 1 -> 300)는 노이즈일 가능성 있으나
                # 본문에 챕터별로 번호가 이어지므로 우선 허용
                valid.append((pos, q_num, question))
                prev_q = q_num
            elif q_num == prev_q:
                # 같은 번호 재등장(예: 답변 중 인용) → 무시
                continue
            else:
                # 번호가 줄어듦 → 노이즈(법령 인용 등)로 보고 무시
                continue

        # 중복 q_num 제거 (이미 위에서 prev_q 기준으로 걸러졌으나 안전하게 한 번 더)
        seen: dict[int, tuple[int, int, str]] = {}
        for pos, q_num, question in valid:
            seen[q_num] = (pos, q_num, question)

        return sorted(seen.values(), key=lambda x: x[0])

    def _build_chapter_map(self, lines: list[str]) -> dict[int, tuple[str, str]]:
        """각 줄 위치에서의 (챕터, 섹션) 컨텍스트 매핑"""
        chapter_map = {}
        current_chapter = ""
        current_section = ""

        for i, line in enumerate(lines):
            if RE_CHAPTER.match(line):
                current_chapter = line
                current_section = ""
            elif RE_SEC_KOR.match(line):
                current_section = line
            chapter_map[i] = (current_chapter, current_section)

        return chapter_map

    def _build_chunk(
        self,
        lines: list[str],
        start: int,
        end: int,
        q_num: int,
        question: str,
        chapter: str,
        section: str,
    ) -> FAQChunk | None:
        """
        start: Q번호+질문이 있는 줄의 인덱스
        end:   다음 Q번호 줄(또는 끝)의 인덱스
        question: start줄에서 추출한 질문 텍스트(이미 번호 제거됨)
        """
        answer_lines = []
        for i in range(start + 1, end):
            line = lines[i]
            if RE_CHAPTER.match(line):
                # 새 챕터 시작 → 이 Q의 답변은 여기서 끝
                break
            if RE_SEC_KOR.match(line):
                continue
            answer_lines.append(line)

        answer = "\n".join(l for l in answer_lines if l.strip()).strip()

        if not question or not answer:
            return None

        page_content = f"Q{q_num}. {question}\n\n{answer}"

        return FAQChunk(
            page_content=page_content,
            metadata={
                "source":      self.source_name,
                "source_year": self.source_year,
                "chapter":     chapter,
                "section":     section,
                "q_number":    q_num,
                "chunk_level": "qa_pair",
            }
        )

    # ── ChromaDB 저장 ─────────────────────────────────────────────

    def add_to_chroma(self, chunks: list[FAQChunk], collection) -> None:
        if not chunks:
            print("[FAQChunker] 저장할 청크가 없습니다.")
            return
        ids       = [str(uuid.uuid4()) for _ in chunks]
        documents = [c.page_content for c in chunks]
        metadatas = [
            {k: (str(v) if v is not None else "") for k, v in c.metadata.items()}
            for c in chunks
        ]
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"[FAQChunker] {len(chunks)}개 청크 저장 완료")


def print_chunks(chunks: list[FAQChunk], max_content: int = 200) -> None:
    print(f"\n총 {len(chunks)}개 청크\n" + "=" * 70)
    for i, c in enumerate(chunks):
        preview = c.page_content[:max_content].replace("\n", " / ")
        if len(c.page_content) > max_content:
            preview += "..."
        m = c.metadata
        print(
            f"[{i:03d}] Q{str(m.get('q_number')):<5} "
            f"| {str(m.get('chapter',''))[:18]:<18} "
            f"| {str(m.get('section',''))[:15]:<15} "
            f"({len(c.page_content)}자)\n"
            f"      {preview}\n"
        )
