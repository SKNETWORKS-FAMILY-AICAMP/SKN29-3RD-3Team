"""
LH 분양가이드 PDF 4종 청킹 모듈
────────────────────────────────────────────────────────────────
처리 파일:
    분양가이드___분양절차.pdf          → 단일 청크
    분양가이드__신청자격-일반공급pdf.pdf → 3개 청크
    LH_청_신청자격-특별공급.pdf        → 유형별 약 16개 청크
    분양가이드___전매제한.pdf          → 2개 청크

핵심 전처리:
    소득기준 표의 잘린 숫자 재조합
        "9,040,51\n6"         → "9,040,516"
        "11,442,8 12,125,08\n63\n1" → "11,442,863 12,125,081"
────────────────────────────────────────────────────────────────
"""

import re
import uuid
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


# ── 노이즈 패턴 ─────────────────────────────────────────────────

# 제거할 헤더/푸터 줄 패턴
RE_NOISE = re.compile(
    r"^("
    r"\d{2}\.\s+\d+\.\s+\d+"           # "26. 6. 8."
    r"|오전 \d+:\d+|오후 \d+:\d+"       # "오후 9:02"
    r"|분양가이드$"                       # 탭 상단
    r"|공공분양\s*$|신혼희망타운$"        # 탭 메뉴 단독
    r"|소개$|분양절차\s*$"              # 탭 메뉴 단독
    r"|신청자격-일반공급\s*$"            # 탭 메뉴 단독
    r"|신청자격-특별공급\s*$"            # 탭 메뉴 단독
    r"|전매제한 등 안내$"               # 탭 메뉴 단독
    r"|분양가이드 < 분양주택.*"           # 브레드크럼
    r"|https?://\S+"                    # URL
    r"|\d+/\d+$"                       # "1/15" 페이지 번호
    r"|매물정보 조회.*|공급계획.*|분양공고.*"  # 링크 버튼
    r"|인터넷청약신청.*|당첨자 조회.*"     # 링크 버튼
    r")$"
)

# 특수문자(LH 아이콘 등) 제거
RE_SPECIAL = re.compile(r"[\ue907\ue900-\uf8ff]")


@dataclass
class LHChunk:
    page_content: str
    metadata: dict = field(default_factory=dict)


def extract_text(pdf_path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    # 페이지 경계는 "\n"으로 변환 (페이지 사이에서 표/문장이 끊기지 않게 합침)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def remove_noise(text: str) -> str:
    """헤더/푸터/특수문자 제거"""
    lines = []
    for line in text.split("\n"):
        line = RE_SPECIAL.sub("", line).strip()
        if not line:
            continue
        if RE_NOISE.match(line):
            continue
        lines.append(line)
    # 날짜 패턴이 포함된 줄 추가 제거 (페이지 헤더 잔재)
    final = []
    for line in lines:
        if re.search(r'\d{2}\.\s+\d+\.\s+\d+', line) and len(line) < 30:
            continue
        if re.search(r'오[전후]\s+\d+:\d+', line) and len(line) < 20:
            continue
        final.append(line)
    return "\n".join(final)


def merge_broken_numbers(text: str) -> str:
    """
    pypdf 추출 시 표의 큰 숫자가 줄바꿈으로 쪼개지는 문제를 복구.

    케이스1: "...10,485,54\\n1 11,064,819" → "...10,485,541\\n11,064,819"
    케이스2: "200% 15,067,52\\n6"          → "200% 15,067,526"
    케이스3: "10,562,\\n642"               → "10,562,642"  (쉼표로 끝나는 경우)
    케이스4: "120% - 7,039,5\\n24\\n9,802,1\\n15\\n10,562,\\n642"
             → "120% - 7,039,524\\n9,802,115\\n10,562,642"
    케이스5: "14,38\\n4,265"               → "14,384,265"  (다음 줄에 ',' 포함된 추가 그룹)
    케이스6: "...7,461,58\\n8 7,925,010 8,388,43\\n3\\n8,851,85\\n5"
             → "...7,461,588\\n7,925,010 8,388,433\\n8,851,855"
             (한 줄에 여러 숫자가 있고, 그 줄의 처음/끝 모두 잘려있는 경우 -> 재귀적으로 재검사)

    규칙: cur가 ",\\d{0,2}$" (쉼표 + 0~2자리 숫자)로 끝나는 동안 반복해서
          3자리를 채우는 데 필요한 자릿수(need)만큼 다음 줄에서 가져와 합침.
          합친 뒤 cur(또는 분리된 rest)이 다시 같은 패턴으로 끝나면 계속 재검사.
    """
    lines = text.split("\n")
    result = []
    i = 0
    while i < len(lines):
        cur = lines[i]
        i += 1

        while True:
            m_end = re.search(r",(\d{0,2})$", cur)
            if not m_end:
                break
            need = 3 - len(m_end.group(1))
            if need <= 0 or i >= len(lines):
                break

            nxt = lines[i]
            m = re.match(r"^(\d+)((?:,\d+)*)(\s+(.*))?$", nxt)
            if not m:
                break
            digits = m.group(1)
            tail = m.group(2) or ""   # ",4,265" 형태의 추가 그룹 -> 같은 숫자에 합침
            rest = m.group(4)

            if len(digits) <= need:
                cur = cur + digits + tail
                i += 1
                if rest:
                    result.append(cur)
                    cur = rest
                # cur(또는 새 cur=rest)이 다시 ",\d{0,2}$"로 끝날 수 있으므로 재검사 계속
                continue
            else:
                cur = cur + digits[:need]
                remainder = digits[need:] + tail
                i += 1
                result.append(cur)
                cur = remainder + (" " + rest if rest else "")
                continue

        result.append(cur)
    return "\n".join(result)


def clean_income_table(text: str) -> str:
    """소득기준 표의 잘린 숫자를 재조합"""
    return merge_broken_numbers(text)


# ── 섹션 분리 유틸 ───────────────────────────────────────────────

def split_at_keywords(text: str, keywords: list[str]) -> dict[str, str]:
    """
    키워드 목록 기준으로 텍스트를 섹션으로 분리.
    반환: {키워드: 해당 섹션 텍스트}
    """
    sections = {}
    positions = []

    for kw in keywords:
        pos = text.find(kw)
        if pos != -1:
            positions.append((pos, kw))

    positions.sort()

    for idx, (pos, kw) in enumerate(positions):
        end = positions[idx + 1][0] if idx + 1 < len(positions) else len(text)
        sections[kw] = text[pos:end].strip()

    return sections


# ── 개별 파일 청킹 ───────────────────────────────────────────────

def chunk_procedure(pdf_path: str) -> list[LHChunk]:
    """분양절차 → 단일 청크"""
    raw  = extract_text(pdf_path)
    text = clean_income_table(remove_noise(raw))

    # STEP01부터 실제 내용 추출
    step_pos = text.find("STEP01")
    if step_pos != -1:
        text = "아파트 분양절차 (LH 공공분양)\n\n" + text[step_pos:]

    return [LHChunk(
        page_content=text.strip(),
        metadata={
            "source":        "LH 분양가이드",
            "source_year":   "2026",
            "page":          "분양절차",
            "chunk_level":   "document",
            "section_title": "아파트 분양절차",
        }
    )]


def chunk_general_supply(pdf_path: str) -> list[LHChunk]:
    """일반공급 → 3개 청크 (자격조건+선정방법 / 소득기준 / 자산기준+출산완화)"""
    raw  = extract_text(pdf_path)
    text = clean_income_table(remove_noise(raw))

    chunks = []

    # ① 자격조건 + 선정방법 + 순위
    qual_end = text.find("소득기준")
    if qual_end == -1:
        qual_end = len(text)
    qual_text = text[:qual_end].strip()

    chunks.append(LHChunk(
        page_content=qual_text,
        metadata={
            "source": "LH 분양가이드", "source_year": "2026",
            "page": "신청자격-일반공급", "chunk_level": "section",
            "section_title": "입주자격 및 선정방법",
        }
    ))

    # ② 소득기준 표
    income_start = text.find("소득기준")
    asset_start  = text.find("자산기준", income_start + 1) if income_start != -1 else -1

    if income_start != -1:
        income_end = asset_start if asset_start != -1 else len(text)
        income_text = text[income_start:income_end].strip()
        chunks.append(LHChunk(
            page_content=income_text,
            metadata={
                "source": "LH 분양가이드", "source_year": "2026",
                "page": "신청자격-일반공급", "chunk_level": "income_table",
                "section_title": "소득기준",
            }
        ))

    # ③ 자산기준 + 출산가구 완화
    if asset_start != -1:
        asset_text = text[asset_start:].strip()
        chunks.append(LHChunk(
            page_content=asset_text,
            metadata={
                "source": "LH 분양가이드", "source_year": "2026",
                "page": "신청자격-일반공급", "chunk_level": "section",
                "section_title": "자산기준 및 출산가구 기준완화",
            }
        ))

    return chunks


# 특별공급 유형 목록
SPECIAL_SUPPLY_TYPES = [
    "다자녀(2자녀 이상)가구 특별공급",
    "노부모부양 특별공급",
    "신혼부부 특별공급",
    "생애최초 특별공급",
    "신생아 특별공급",
    "국가유공자 특별공급",
    "기관추천 특별공급",
]


def chunk_special_supply(pdf_path: str) -> list[LHChunk]:
    """특별공급 → 유형별 청크 (자격+당첨기준 / 소득기준 표)"""
    raw  = extract_text(pdf_path)
    text = clean_income_table(remove_noise(raw))

    # 유형별 섹션 분리
    sections = split_at_keywords(text, SPECIAL_SUPPLY_TYPES)

    chunks = []
    for supply_type, section_text in sections.items():
        if not section_text.strip():
            continue

        # 소득기준 표 위치 찾기
        income_pos = section_text.find("소득기준")
        asset_pos  = section_text.find("자산기준")

        if income_pos == -1:
            # 소득기준 표 없음 (국가유공자, 기관추천) → 단일 청크
            chunks.append(LHChunk(
                page_content=section_text.strip(),
                metadata={
                    "source": "LH 분양가이드", "source_year": "2026",
                    "page": "신청자격-특별공급",
                    "supply_type": supply_type,
                    "chunk_level": "supply_type",
                    "section_title": "자격조건",
                }
            ))
            continue

        # ① 자격조건 + 당첨자선정기준
        qual_text = section_text[:income_pos].strip()
        # 당첨자선정 기준이 소득기준 표 뒤에 있는 경우 포함
        award_pos = section_text.find("당첨자")
        if award_pos != -1 and award_pos > income_pos:
            award_text = section_text[award_pos:].strip()
            if asset_pos != -1:
                award_text = section_text[award_pos:].strip()
            qual_text = qual_text + "\n\n" + award_text if qual_text else award_text

        chunks.append(LHChunk(
            page_content=(section_text[:income_pos].strip()),
            metadata={
                "source": "LH 분양가이드", "source_year": "2026",
                "page": "신청자격-특별공급",
                "supply_type": supply_type,
                "chunk_level": "supply_type",
                "section_title": "자격조건 및 당첨기준",
            }
        ))

        # ② 소득기준 표 (+ 자산기준)
        income_end = len(section_text)
        # 당첨자선정기준 이전까지만 소득표로
        if award_pos != -1 and award_pos > income_pos:
            income_end = award_pos

        income_text = section_text[income_pos:income_end].strip()
        if income_text:
            chunks.append(LHChunk(
                page_content=income_text,
                metadata={
                    "source": "LH 분양가이드", "source_year": "2026",
                    "page": "신청자격-특별공급",
                    "supply_type": supply_type,
                    "chunk_level": "income_table",
                    "section_title": "소득기준 및 자산기준",
                }
            ))

    # 출산가구 기준완화 공통표 (문서 마지막 부분)
    common_pos = text.rfind("출산가구 기준완화")
    if common_pos != -1:
        # 마지막 특별공급 섹션 이후에 있는 공통표
        last_type_pos = max(
            text.find(t) for t in SPECIAL_SUPPLY_TYPES if text.find(t) != -1
        )
        common_section = text[common_pos:] if common_pos > last_type_pos else ""
        if common_section.strip():
            chunks.append(LHChunk(
                page_content=common_section.strip(),
                metadata={
                    "source": "LH 분양가이드", "source_year": "2026",
                    "page": "신청자격-특별공급",
                    "supply_type": "공통",
                    "chunk_level": "income_table",
                    "section_title": "출산가구 소득·자산기준 완화 (공통)",
                }
            ))

    return chunks


def chunk_transfer_limit(pdf_path: str) -> list[LHChunk]:
    """전매제한 → 2개 청크 (전매제한 / 거주의무)"""
    raw  = extract_text(pdf_path)
    text = clean_income_table(remove_noise(raw))

    chunks = []

    # ① 전매제한 (제도개요 + 전매제한기간 표)
    # "전매제한 및 거주의무기간 안내" 제목 이후부터 실제 내용
    content_start = text.find("제도개요")
    if content_start == -1:
        content_start = text.find("전매제한기간")
    if content_start == -1:
        content_start = 0
    text = text[content_start:]

    resid_pos = text.find("거주의무기간")
    transfer_text = text[:resid_pos].strip() if resid_pos != -1 else text.strip()

    chunks.append(LHChunk(
        page_content=transfer_text,
        metadata={
            "source": "LH 분양가이드", "source_year": "2026",
            "page": "전매제한",
            "chunk_level": "section",
            "section_title": "전매제한 제도 및 제한기간",
        }
    ))

    # ② 거주의무기간
    if resid_pos != -1:
        resid_text = text[resid_pos:].strip()
        chunks.append(LHChunk(
            page_content=resid_text,
            metadata={
                "source": "LH 분양가이드", "source_year": "2026",
                "page": "전매제한",
                "chunk_level": "section",
                "section_title": "거주의무기간",
            }
        ))

    return chunks


# ── 메인 클래스 ──────────────────────────────────────────────────

class LHGuideChunker:
    def __init__(
        self,
        procedure_pdf:      str = None,
        general_supply_pdf: str = None,
        special_supply_pdf: str = None,
        transfer_limit_pdf: str = None,
        source_year:        str = "2026",
    ):
        self.procedure_pdf      = procedure_pdf
        self.general_supply_pdf = general_supply_pdf
        self.special_supply_pdf = special_supply_pdf
        self.transfer_limit_pdf = transfer_limit_pdf
        self.source_year        = source_year

    def chunk(self) -> list[LHChunk]:
        chunks = []

        if self.procedure_pdf and Path(self.procedure_pdf).exists():
            chunks.extend(chunk_procedure(self.procedure_pdf))

        if self.general_supply_pdf and Path(self.general_supply_pdf).exists():
            chunks.extend(chunk_general_supply(self.general_supply_pdf))

        if self.special_supply_pdf and Path(self.special_supply_pdf).exists():
            chunks.extend(chunk_special_supply(self.special_supply_pdf))

        if self.transfer_limit_pdf and Path(self.transfer_limit_pdf).exists():
            chunks.extend(chunk_transfer_limit(self.transfer_limit_pdf))

        # source_year 덮어쓰기
        for c in chunks:
            c.metadata["source_year"] = self.source_year

        return chunks

    def add_to_chroma(self, chunks: list[LHChunk], collection) -> None:
        if not chunks:
            print("[LHGuideChunker] 저장할 청크가 없습니다.")
            return

        ids       = [str(uuid.uuid4()) for _ in chunks]
        documents = [c.page_content for c in chunks]
        metadatas = [
            {k: (str(v) if v is not None else "") for k, v in c.metadata.items()}
            for c in chunks
        ]
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"[LHGuideChunker] {len(chunks)}개 청크 저장 완료")


# ── 확인용 출력 ──────────────────────────────────────────────────

def print_chunks(chunks: list[LHChunk], max_content: int = 200) -> None:
    print(f"\n총 {len(chunks)}개 청크\n" + "=" * 75)
    for i, c in enumerate(chunks):
        preview = c.page_content[:max_content].replace("\n", " / ")
        if len(c.page_content) > max_content:
            preview += "..."
        m = c.metadata
        print(
            f"[{i:02d}] {m.get('page',''):<16} "
            f"| {m.get('chunk_level',''):<14} "
            f"| {str(m.get('supply_type', m.get('section_title','')))[:25]:<25} "
            f"({len(c.page_content)}자)\n"
            f"      {preview}\n"
        )
