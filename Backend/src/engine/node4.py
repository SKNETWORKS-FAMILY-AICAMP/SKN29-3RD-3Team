"""Node 4: 공고문 입력 인터럽트 노드

그래프를 일시정지하고 사용자로부터 공고문 정보를 자유 형식으로 입력받아
OpenAI with_structured_output으로 정형 데이터로 변환합니다.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, Optional

from langchain_openai import ChatOpenAI
from langgraph.types import interrupt
from pydantic import BaseModel, Field


# ── 공고문 정형 스키마 ─────────────────────────────────────────────

class AnnouncementSchema(BaseModel):
    """사용자의 자유 입력에서 공고문 필수 데이터를 추출합니다."""

    region: str = Field(
        ...,
        description="단지가 위치한 지역 및 자치구 (예: '서울 강남구', '경기 수원시')"
    )
    is_regulated: bool = Field(
        ...,
        description="투기과열지구, 조정대상지역 등 규제지역이면 True, 비규제지역이면 False"
    )
    supply_type: Literal["민간", "공공", "미정"] = Field(
        ...,
        description="민간분양/민영주택은 '민간', 공공분양/LH/SH/국민주택은 '공공'"
    )
    price: Optional[int] = Field(
        None,
        description="분양가를 원 단위 정수로 환산 (예: '5억' → 500000000). 없으면 null"
    )
    deposit: Optional[int] = Field(
        None,
        description="임대/전세보증금을 원 단위 정수로 환산. 일반 분양이면 null"
    )
    area: str = Field(
        ...,
        description="희망 평형 또는 전용면적 (예: '84㎡', '59㎡', '34평')"
    )
    supply_count: Optional[int] = Field(
        None,
        description="공급 세대수 (예: '80세대' → 80). 없으면 null"
    )


# ── Node 4 메인 함수 ──────────────────────────────────────────────

def run_node4(state: Mapping[str, Any]) -> dict[str, Any]:
    """
    그래프를 일시정지하고 사용자 입력을 기다립니다.
    FastAPI에서 Command(resume=announcement_text)로 재개하면
    자유 텍스트를 정형 데이터로 변환해 State에 저장합니다.
    """
    # 그래프 일시정지 + 프론트 대기 메시지
    user_raw_input: str = interrupt(
        {"prompt": "관심 단지의 지역, 규제여부, 공급유형, 분양가, 평형 정보를 자유롭게 입력해주세요."}
    )

    # 자유 텍스트 → 정형 데이터 변환
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured_llm = llm.with_structured_output(AnnouncementSchema, method="function_calling")
    extracted: AnnouncementSchema = structured_llm.invoke(user_raw_input)
    announcement = extracted.model_dump()

    return {
        "announcement": announcement,
    }