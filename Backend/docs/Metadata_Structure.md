# ChromaDB Collection별 Metadata 구조

청약 RAG에서 사용하는 6개 collection의 metadata 필드를 정리한 문서입니다.

| Collection | 청크 수 | 원본 문서 |
|---|---|---|
| law_chunks | 163개 | 주택공급에 관한 규칙 (HWP) |
| faq_chunks | 183개 | 2024 주택청약 FAQ (PDF) |
| manual_chunks | 143개 | 주택공급 업무매뉴얼 (PDF) |
| lh_guide_chunks | 18개 | LH 분양가이드 4종 (PDF) |
| web_faq_chunks | 120개 | 청약홈/마이홈포털 FAQ (JSON) |
| guide_chunks | 72개 | 청약제도안내 (Markdown) |

---

## 1. law_chunks (법령)

```python
{
    "law":           "주택공급에 관한 규칙",
    "chapter":       "제4장 주택공급 방법",   # 장 제목 (없으면 "")
    "article":       "41",                   # 조 번호
    "article_title": "신혼부부 특별공급",
    "paragraph":     "3",                    # 항 번호 (없으면 "")
    "item":          "2",                    # 호 번호 (없으면 "")
    "item_sub":      "가",                   # 목 (없으면 "")
    "chunk_level":   "article" | "paragraph" | "item" | "item_sub",
}
```

> **주의**: 다른 5개 collection과 달리 `source`, `source_year` 필드가 없습니다. 출처 표기 시 `law` 필드를 사용합니다.

---

## 2. faq_chunks (2024 주택청약 FAQ)

```python
{
    "source":      "2024 주택청약 FAQ",
    "source_year": "2024",
    "chapter":     "Ⅰ. 청약자격(공통)",   # 대분류
    "section":     "나. 청약신청지역 및 우선공급",  # 중분류 (없을 수 있음)
    "q_number":    98,                     # 정수, 1~480
    "chunk_level": "qa_pair",
}
```

---

## 3. manual_chunks (주택공급 업무매뉴얼)

`part` 값에 따라 구조가 다릅니다.

### 3-1. 본문 - 절 단위 (`chunk_level: "section"`)

```python
{
    "source":        "주택공급 업무 매뉴얼",
    "source_year":   "2017",
    "part":          "본문",
    "chapter":       "제4장",
    "chapter_title": "주택공급 방법",
    "section":       "제4절",
    "section_title": "특별공급",
    "subsection":    "",
    "chunk_level":   "section",
}
```

### 3-2. 본문 - 소제목 단위 (`chunk_level: "subsection"`)

긴 절을 소제목 단위로 추가 분할한 경우입니다. `subsection`에 실제 소제목명, 또는 절 도입부인 경우 `"(도입)"`이 들어갑니다.

```python
{
    "source":        "주택공급 업무 매뉴얼",
    "source_year":   "2017",
    "part":          "본문",
    "chapter":       "제4장",
    "chapter_title": "주택공급 방법",
    "section":       "제4절",
    "section_title": "특별공급",
    "subsection":    "신혼부부 특별공급",   # 또는 "(도입)"
    "chunk_level":   "subsection",
}
```

### 3-3. 질의응답 (`chunk_level: "qa_pair"`)

```python
{
    "source":        "주택공급 업무 매뉴얼",
    "source_year":   "2017",
    "part":          "질의답변",
    "chapter":       "제4장",
    "chapter_title": "주택공급 방법",
    "q_number":      "Q4-37",   # 문자열형 (예: "Q4-37")
    "chunk_level":   "qa_pair",
}
```

---

## 4. lh_guide_chunks (LH 분양가이드)

공통 필드: `source`, `source_year`, `page`, `chunk_level`, `section_title`

| page | chunk_level | 추가 필드 | 설명 |
|---|---|---|---|
| 분양절차 | document | - | 절차 안내 |
| 신청자격-일반공급 | section / income_table | - | 자격조건/소득표/자산 |
| 신청자격-특별공급 | supply_type / income_table | `supply_type` | 특별공급 유형별 |
| 전매제한 | section | - | 전매제한/거주의무 |

```python
{
    "source":        "LH 분양가이드",
    "source_year":   "2026",
    "page":          "신청자격-특별공급",
    "supply_type":   "신혼부부 특별공급",   # supply_type 청크에만 존재. 공통표는 "공통"
    "chunk_level":   "supply_type" | "income_table" | "section" | "document",
    "section_title": "자격조건 및 당첨기준",
}
```

### page별 chunk_level 조합

- **분양절차**: `document`
- **신청자격-일반공급**: `section`(자격/선정방법, 자산기준), `income_table`(소득기준)
- **신청자격-특별공급**: `supply_type`(자격조건/당첨기준), `income_table`(소득·자산기준, 공통완화표)
- **전매제한**: `section`(전매제한 제도/기간, 거주의무기간)

---

## 5. web_faq_chunks (청약홈/마이홈포털 FAQ)

출처에 따라 필드 구성이 다릅니다.

### 5-1. 마이홈포털

```python
{
    "source":      "마이홈포털",
    "source_year": "2026",
    "scope":       "아파트 매매/분양청약",
    "category":    "공공분양",
    "ntt_id":      "728",
    "chunk_level": "qa_pair",
}
```

### 5-2. 청약홈

```python
{
    "source":      "청약홈",
    "source_year": "2026",
    "scope":       "아파트 매매/분양청약",
    "category":    "청약통장",          # 대분류 5종 중 하나
    "subcategory": "청약통장의 가입",    # 소분류
    "bbs_no":      "3000",
    "bbs_sn":      "28",
    "chunk_level": "qa_pair",
}
```

> 청약홈 `category` 5종: 청약통장, 청약가점제, 청약 제한, 분양권 전매, 청약이 잘 안되세요?

---

## 6. guide_chunks (청약제도안내, Markdown)

```python
{
    "Header_1":    "청약제도안내 - 특별공급",        # 원본 10개 .md 파일 단위 (없으면 None/"")
    "Header_2":    "생애최초 주택구입 특별공급",      # 없을 수 있음
    "Header_3":    "생애최초 (공공주택)",            # 없을 수 있음
    "source":      "청약Home 청약제도안내",
    "source_year": "2026",
    "doc_title":   "청약제도안내 - 특별공급",        # = Header_1과 동일값
    "chunk_level": "section" | "table",
}
```

- `chunk_level: "table"` → 표가 포함되어 표 인식 분할/자연어 변환(`표 설명:`)이 적용된 청크
- `chunk_level: "section"` → 표가 없거나 1,200자 이내라 분할이 필요 없었던 일반 섹션
- 모든 청크 본문 맨 앞에 `[Header_1 > Header_2 > Header_3]` 형태의 prefix가 삽입되어 있음

---

## 공통 필드 요약

| 필드 | law_chunks | faq_chunks | manual_chunks | lh_guide_chunks | web_faq_chunks | guide_chunks |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `source` | ❌ (`law`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `source_year` | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `chunk_level` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

`source_year` 값 분포: `2017`(manual), `2024`(faq), `2026`(lh_guide, web_faq, guide) — law_chunks만 연도 정보 없음. 최신 자료 우선 검색/가중치 적용 시 이 필드를 활용할 수 있습니다.

---

## retriever.py의 format_source() 매핑

각 collection의 metadata는 `retriever.py`의 `format_source()`에서 다음과 같이 사람이 읽을 수 있는 출처 라벨로 변환됩니다.

```python
law_chunks       → "주택공급에 관한 규칙 제41조(신혼부부 특별공급) 제3항"
faq_chunks       → "2024 주택청약 FAQ Q98"
manual_chunks    → "주택공급 업무 매뉴얼 Q4-37"
                   또는 "주택공급 업무 매뉴얼 제4장 제4절 특별공급"
lh_guide_chunks  → "LH 분양가이드 - 신혼부부 특별공급"
web_faq_chunks   → "청약홈 - 청약통장 (청약통장의 가입)"
guide_chunks     → "청약Home 청약제도안내 - 특별공급 > 생애최초 (공공주택)"
```