"""
주택공급 업무 매뉴얼 PDF 청킹 모듈
────────────────────────────────────────────────────────────────
사용법:
    from manual_chunker import ManualChunker, print_chunks

    chunker = ManualChunker("주택공급_업무_매뉴얼.pdf")
    chunks = chunker.chunk()
    print_chunks(chunks)

    import chromadb
    client = chromadb.PersistentClient(path="./chroma_db")
    col = client.get_or_create_collection("manual_chunks")
    chunker.add_to_chroma(chunks, col)
────────────────────────────────────────────────────────────────
문서 구조:
    Ⅰ. 본문     → 절(節) 단위 청킹 (2,000자 초과 시 소제목 단위 분리)
    Ⅱ. 질의 답변 → Q&A 쌍 단위 청킹 (Q장번호-번호. 패턴)

source_year="2017" 명시 → 2024 FAQ와 중복 검색 시 필터링 가능
────────────────────────────────────────────────────────────────
"""

import re
import uuid
from dataclasses import dataclass, field



# ── 임계값 ──────────────────────────────────────────────────────
SECTION_THRESHOLD = 1500   # 이 이상이면 소제목 단위로 분리


# ── 패턴 ────────────────────────────────────────────────────────

RE_FF = re.compile(r"\f")

# 장 제목: "제1장", "제1장\n주택공급 업무의 개요"
RE_CHAPTER_NUM  = re.compile(r"^제(\d+)장$")
RE_CHAPTER_FULL = re.compile(r"^제(\d+)장\s+(.+)$")

# 절 제목: "제1절 목적", "제2절 법원(法源)"
RE_SECTION = re.compile(r"^제(\d+)절\s+(.+)$")

# Q번호: "Q1-1.", "Q4-12."
RE_Q = re.compile(r"^(Q(\d+)-(\d+))\.\s+(.+)$")

# 본문 소제목: "1. 국민주택의 입주자선정", "1) 국민주택 특별공급"
RE_SUBSEC_NUM = re.compile(r"^(\d+)\.\s+[가-힣]")
RE_SUBSEC_IDX = re.compile(r"^(\d+)\)\s+[가-힣]")

# 제거할 헤더/푸터
RE_SKIP = re.compile(
    r"^(주택공급 업무 매뉴얼|Ⅰ\. 본 문|Ⅱ\. 질의 답변|\d{1,3})$"
)

# 목차 판별: 점선 3줄 이상
RE_DOTS = re.compile(r"[·ㆍ]{3,}|\.{4,}")

# 파트 구분 디자인 페이지: 짧고 "본 문" or "질의 답변"만 있음
RE_PART_PAGE = re.compile(r"^(본\s*문|질의\s*답변)$")


@dataclass
class ManualChunk:
    page_content: str
    metadata: dict = field(default_factory=dict)


def extract_text(pdf_path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    return "\f".join(page.extract_text() or "" for page in reader.pages)


def is_skip_page(page_text: str) -> bool:
    """목차, 표지, 파트 구분 디자인 페이지 제거"""
    stripped = page_text.strip()
    # 목차: 점선 3줄 이상
    if sum(1 for l in stripped.split("\n") if RE_DOTS.search(l)) >= 3:
        return True
    # 파트 구분 페이지: 내용이 거의 없고 "본 문" or "질의 답변"만
    if len(stripped) < 30 and RE_PART_PAGE.search(stripped):
        return True
    return False


def normalize_spaced_q_line(line: str) -> str:
    """
    'Q 4 - 1 0 . 아 내 가  결 혼  전 ...' 처럼 PDF 렌더링 이슈로
    한 글자(또는 숫자)마다 공백이 들어간 비정상 Q번호 줄을 정규화.

    감지 기준: "Q" 다음에 공백+숫자가 오는 경우 (정상 "Q4-10."은 Q 바로 뒤에
    숫자가 붙어있어 영향받지 않음)

    -> 모든 공백을 제거한 뒤 "Q번호." 뒤에 공백 1개를 삽입해
       RE_Q (r"^(Q(\\d+)-(\\d+))\\.\\s+(.+)$") 패턴과 호환되게 만듦.
       (본문 내 띄어쓰기는 사라지지만 검색/임베딩에는 지장 없음)
    """
    if re.match(r"^Q\s+\d", line):
        compact = line.replace(" ", "")
        compact = re.sub(r"^(Q\d+-\d+\.)", r"\1 ", compact)
        return compact
    return line


def clean_lines(raw: str) -> list[str]:
    pages = RE_FF.split(raw)
    lines = []
    for page in pages:
        if is_skip_page(page):
            continue
        for line in page.split("\n"):
            line = line.strip()
            if not line:
                continue
            if RE_SKIP.match(line):
                continue
            line = normalize_spaced_q_line(line)
            lines.append(line)
    return lines


# ── 본문 파트 청킹 ──────────────────────────────────────────────

def split_body(lines: list[str]) -> list[ManualChunk]:
    """
    절(節) 단위로 분리. 2,000자 초과 시 소제목 단위로 추가 분리.
    """
    chapters = {}   # 절 시작 위치 → (장번호, 장제목, 절번호, 절제목)
    current_chapter_num   = ""
    current_chapter_title = ""

    # 장/절 위치 수집
    section_positions = []
    for i, line in enumerate(lines):
        mc = RE_CHAPTER_NUM.match(line)
        mf = RE_CHAPTER_FULL.match(line)
        if mc:
            current_chapter_num   = mc.group(1)
            current_chapter_title = ""  # 다음 줄에서 제목 보완
        elif mf:
            current_chapter_num   = mf.group(1)
            current_chapter_title = mf.group(2).strip()
        # 장 번호만 있는 경우 다음 줄이 제목
        elif (i > 0 and RE_CHAPTER_NUM.match(lines[i-1])
              and not RE_SECTION.match(line)
              and not RE_SKIP.match(line)
              and current_chapter_title == ""):
            current_chapter_title = line

        ms = RE_SECTION.match(line)
        if ms:
            section_positions.append((
                i,
                f"제{current_chapter_num}장",
                current_chapter_title,
                f"제{ms.group(1)}절",
                ms.group(2).strip(),
            ))

    chunks = []
    for idx, (pos, ch_num, ch_title, sec_num, sec_title) in enumerate(section_positions):
        end = section_positions[idx + 1][0] if idx + 1 < len(section_positions) else len(lines)
        section_lines = lines[pos:end]
        section_text  = "\n".join(l for l in section_lines if l.strip())

        prefix = f"{ch_num} {sec_num} {sec_title}"

        if len(section_text) <= SECTION_THRESHOLD:
            # 절 통째로 하나의 청크
            chunks.append(ManualChunk(
                page_content=section_text,
                metadata={
                    "source":        "주택공급 업무 매뉴얼",
                    "source_year":   "2017",
                    "part":          "본문",
                    "chapter":       ch_num,
                    "chapter_title": ch_title,
                    "section":       sec_num,
                    "section_title": sec_title,
                    "subsection":    "",
                    "chunk_level":   "section",
                }
            ))
        else:
            # 소제목 단위로 분리
            sub_chunks = split_by_subsection(
                section_lines, ch_num, ch_title, sec_num, sec_title
            )
            chunks.extend(sub_chunks)

    return chunks


def split_by_subsection(
    lines: list[str],
    ch_num: str, ch_title: str,
    sec_num: str, sec_title: str,
) -> list[ManualChunk]:
    """
    소제목("1. 제목", "1) 제목", 특별공급 유형 번호 등) 단위로 분리.
    소제목이 없으면 절 통째로 반환.
    """
    # 소제목 위치 수집
    sub_positions = []
    for i, line in enumerate(lines):
        if i == 0:
            continue  # 절 제목 자체는 제외
        if RE_SUBSEC_NUM.match(line) or RE_SUBSEC_IDX.match(line):
            sub_positions.append((i, line.strip()))

    if not sub_positions:
        # 소제목 없으면 절 통째로
        text = "\n".join(l for l in lines if l.strip())
        return [ManualChunk(
            page_content=text,
            metadata={
                "source": "주택공급 업무 매뉴얼", "source_year": "2017",
                "part": "본문", "chapter": ch_num, "chapter_title": ch_title,
                "section": sec_num, "section_title": sec_title,
                "subsection": "", "chunk_level": "section",
            }
        )]

    chunks = []

    def make_chunk(sub_lines, sub_title):
        text = f"{sec_num} {sec_title}\n" + "\n".join(l for l in sub_lines if l.strip())
        return ManualChunk(
            page_content=text,
            metadata={
                "source": "주택공급 업무 매뉴얼", "source_year": "2017",
                "part": "본문", "chapter": ch_num, "chapter_title": ch_title,
                "section": sec_num, "section_title": sec_title,
                "subsection": sub_title, "chunk_level": "subsection",
            }
        )

    # 첫 소제목 이전 텍스트 (절 도입부)
    intro = lines[:sub_positions[0][0]]
    if any(l.strip() for l in intro):
        intro_text = f"{sec_num} {sec_title}\n" + "\n".join(l for l in intro if l.strip())
        chunks.append(ManualChunk(
            page_content=intro_text,
            metadata={
                "source": "주택공급 업무 매뉴얼", "source_year": "2017",
                "part": "본문", "chapter": ch_num, "chapter_title": ch_title,
                "section": sec_num, "section_title": sec_title,
                "subsection": "(도입)", "chunk_level": "subsection",
            }
        ))

    # 소제목별 청크
    for idx, (pos, sub_title) in enumerate(sub_positions):
        end = sub_positions[idx + 1][0] if idx + 1 < len(sub_positions) else len(lines)
        sub_lines = lines[pos:end]

        # 인접한 짧은 소제목들은 병합 (누적 길이 기준)
        # 단순화: 각 소제목을 개별 청크로 생성
        chunks.append(make_chunk(sub_lines, sub_title))

    return chunks


# ── 질의 답변 파트 청킹 ─────────────────────────────────────────

# 장 제목 매핑
QA_CHAPTER_TITLES = {
    "1": "주택공급 업무의 개요",
    "2": "입주자저축",
    "3": "입주자 모집 및 주택공급 신청",
    "4": "주택공급 방법",
    "5": "입주자 선정 업무 및 관리",
    "6": "11.3 대책 관련 1순위 및 재당첨 제한 강화 등",
}


def split_qa(lines: list[str]) -> list[ManualChunk]:
    """Q번호 패턴(Q장-번호.) 기준으로 Q&A 쌍 분리"""
    # Q 위치 수집
    q_positions = []
    for i, line in enumerate(lines):
        m = RE_Q.match(line)
        if m:
            q_positions.append((i, m.group(1), m.group(2), m.group(3), m.group(4)))

    chunks = []
    for idx, (pos, q_id, ch_num, q_num, question_start) in enumerate(q_positions):
        end = q_positions[idx + 1][0] if idx + 1 < len(q_positions) else len(lines)

        # 질문: 여러 줄에 걸칠 수 있음 (다음 "A "가 나올 때까지)
        question_lines = [question_start]
        answer_lines   = []
        in_answer = False

        for line in lines[pos + 1:end]:
            if RE_SKIP.match(line):
                continue
            if line.startswith("A ") and not in_answer:
                in_answer = True
                answer_lines.append(line[2:].strip())  # "A " 제거
            elif in_answer:
                answer_lines.append(line)
            else:
                question_lines.append(line)

        question = " ".join(q.strip() for q in question_lines if q.strip())
        answer   = "\n".join(a for a in answer_lines if a.strip()).strip()

        if not question or not answer:
            continue

        ch_title = QA_CHAPTER_TITLES.get(ch_num, f"제{ch_num}장")
        page_content = f"{q_id}. {question}\n\n{answer}"

        chunks.append(ManualChunk(
            page_content=page_content,
            metadata={
                "source":        "주택공급 업무 매뉴얼",
                "source_year":   "2017",
                "part":          "질의답변",
                "chapter":       f"제{ch_num}장",
                "chapter_title": ch_title,
                "q_number":      q_id,
                "chunk_level":   "qa_pair",
            }
        ))

    return chunks


# ── 메인 클래스 ──────────────────────────────────────────────────

class ManualChunker:
    def __init__(
        self,
        pdf_path: str,
        source_name: str = "주택공급 업무 매뉴얼",
        source_year: str = "2017",
    ):
        self.pdf_path    = pdf_path
        self.source_name = source_name
        self.source_year = source_year

    def chunk(self) -> list[ManualChunk]:
        """PDF 전체 → ManualChunk 리스트 (본문 + 질의답변)"""
        raw = extract_text(self.pdf_path)

        # 파트 분리는 raw 텍스트 단계에서 먼저 수행
        # "Ⅱ. 질의 답변"이 clean_lines의 RE_SKIP에 걸리기 전에 분리
        # → 목차(첫 번째)와 헤더 반복을 제외하고, 파트 구분 디자인 페이지() 직후를 찾음
        ii_marker = "Ⅱ. 질의 답변"
        # 폼피드() 직후에 나오는 "Ⅱ. 질의 답변" = 실제 질의답변 파트 시작
        import re as _re
        ii_match = _re.search(r'\f\s*Ⅱ\. 질의 답변\s*\n\s*제1장', raw)
        if ii_match:
            ii_pos = ii_match.start()
            raw_body = raw[:ii_pos]
            raw_qa   = raw[ii_pos:]
        else:
            # fallback: 두 번째 등장 위치
            first  = raw.find(ii_marker)
            second = raw.find(ii_marker, first + 1) if first != -1 else -1
            if second != -1:
                raw_body = raw[:second]
                raw_qa   = raw[second:]
            else:
                raw_body = raw
                raw_qa   = ""

        body_lines = clean_lines(raw_body)
        qa_lines   = clean_lines(raw_qa)

        body_chunks = split_body(body_lines)
        qa_chunks   = split_qa(qa_lines)

        # source_name / source_year 덮어쓰기
        for c in body_chunks + qa_chunks:
            c.metadata["source"]      = self.source_name
            c.metadata["source_year"] = self.source_year

        return body_chunks + qa_chunks

    def _find_qa_start(self, lines: list[str]) -> int:
        """'Ⅱ. 질의 답변' 또는 첫 Q번호 줄 위치 반환"""
        for i, line in enumerate(lines):
            if "Ⅱ. 질의 답변" in line:
                return i
            if RE_Q.match(line) and i > len(lines) // 2:
                return i
        return len(lines)

    def add_to_chroma(self, chunks: list[ManualChunk], collection) -> None:
        if not chunks:
            print("[ManualChunker] 저장할 청크가 없습니다.")
            return

        # 8192토큰 초과 방지: 11000자 초과 청크는 절반으로 분할
        final_chunks = []
        for c in chunks:
            if len(c.page_content) > 6000:
                mid = len(c.page_content) // 2
                # 줄바꿈 기준으로 자르기
                split_pos = c.page_content.rfind("\n", 0, mid)
                if split_pos == -1:
                    split_pos = mid
                part1 = c.page_content[:split_pos].strip()
                part2 = c.page_content[split_pos:].strip()
                for part in [part1, part2]:
                    if part:
                        final_chunks.append(ManualChunk(
                            page_content=part,
                            metadata=c.metadata.copy()
                        ))
            else:
                final_chunks.append(c)

        ids       = [str(uuid.uuid4()) for _ in final_chunks]
        documents = [c.page_content for c in final_chunks]
        metadatas = [
            {k: (str(v) if v is not None else "") for k, v in c.metadata.items()}
            for c in final_chunks
        ]
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"[ManualChunker] {len(final_chunks)}개 청크 저장 완료")


# ── 확인용 출력 ──────────────────────────────────────────────────

def print_chunks(chunks: list[ManualChunk], max_content: int = 150) -> None:
    print(f"\n총 {len(chunks)}개 청크\n" + "=" * 75)
    for i, c in enumerate(chunks):
        preview = c.page_content[:max_content].replace("\n", " / ")
        if len(c.page_content) > max_content:
            preview += "..."
        m = c.metadata
        label = m.get('q_number') or m.get('subsection') or m.get('section_title', '')
        print(
            f"[{i:03d}] {m.get('part'):<6} "
            f"| {m.get('chunk_level'):<10} "
            f"| {m.get('chapter'):<6} "
            f"| {str(label)[:25]:<25} "
            f"({len(c.page_content)}자)\n"
            f"      {preview}\n"
        )
