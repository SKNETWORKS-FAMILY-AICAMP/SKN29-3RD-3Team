"""
Node 5 RAG 연동 툴
- check_regional_priority: 지역 우선공급 확인 (3번)
- analyze_subscription_timing: 청약 시점 적합성 분석 (7번)
"""

import os
import sys

import importlib.util
from functools import lru_cache
from pathlib import Path
from types import ModuleType


from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ── retriever.py 경로 설정 ────────────────────────────────────────
RAG_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),  # engine/tools/
    "..", "..", "rag"                             # src/rag/
)
sys.path.insert(0, RAG_DIR)

from retriever import search, format_source

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# ── 공통 RAG 답변 생성 함수 ───────────────────────────────────────

def _rag_answer(query: str, system_prompt: str) -> dict:
    """
    retriever로 context를 검색하고 LLM으로 답변을 생성합니다.
    검색 결과가 없으면 found=False를 반환합니다.
    """

    result = search(query)

    retriever = _load_retriever()
    result = retriever.search(query)


    if not result["found"]:
        return {
            "found": False,
            "answer": "제공된 자료에서 관련 정보를 찾을 수 없습니다.",
            "sources": [],
        }

    context_parts = []
    sources = []
    for dist, doc, meta, col_name in result["results"]:

        label = format_source(meta, col_name)

        label = retriever.format_source(meta, col_name)

        context_parts.append(f"[출처: {label}]\n{doc}")
        sources.append({"label": label, "distance": round(dist, 4)})

    context = "\n\n---\n\n".join(context_parts)

    prompt = ChatPromptTemplate.from_template(
        """{system_prompt}

아래 [Context]의 내용에만 기반하여 답변하세요.
Context에 없는 내용은 "제공된 자료에서는 확인할 수 없습니다"라고 명시하세요.
마크다운 헤더(#, ##)나 굵은글씨(**)는 사용하지 마세요.
답변 마지막에 추가 질문 유도 멘트는 넣지 마세요.

[Context]
{context}

질문: {query}

답변:"""
    )


    chain = prompt | llm | StrOutputParser()

    chain = prompt | ChatOpenAI(model="gpt-4o-mini", temperature=0) | StrOutputParser()

    answer = chain.invoke({
        "system_prompt": system_prompt,
        "context": context,
        "query": query,
    })

    return {
        "found": True,
        "answer": answer,
        "sources": sources,
    }


@lru_cache(maxsize=1)
def _load_retriever() -> ModuleType:
    retriever_path = Path(__file__).resolve().parents[2] / "rag" / "retriever.py"
    spec = importlib.util.spec_from_file_location("_node5_root_rag_retriever", retriever_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"retriever.py를 찾을 수 없습니다: {retriever_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ── Tool 3: 지역 우선공급 확인 ───────────────────────────────────

@tool
def check_regional_priority(
    user_region: str,
    announcement_region: str,
) -> dict:
    """
    사용자 거주지역과 청약 대상 건설지역을 비교해 지역 우선공급 여부를 확인합니다.

    Args:
        user_region: 사용자 거주지역 (예: "서울")
        announcement_region: 청약 대상 건설지역 (예: "서울 강남구")

    Returns:
        dict: {
            "found": 정보 검색 성공 여부,
            "answer": 우선공급 관련 분석 답변,
            "sources": 참고 출처 목록,
            "is_same_region": 거주지역과 건설지역 일치 여부,
        }
    """
    query = (
        f"{announcement_region}에서 분양하는 주택의 해당지역 거주자 "
        f"우선공급 기준이 뭐야? 거주지역 {user_region} 거주자가 "
        f"1순위로 우선 공급받을 수 있어?"
    )

    system_prompt = (
        "당신은 대한민국 주택 청약 제도 전문가입니다. "
        "지역 우선공급 기준에 대해 사용자의 거주지역과 청약 대상 지역을 비교해 "
        "구체적으로 설명해주세요."
    )

    result = _rag_answer(query, system_prompt)

    # 거주지역과 건설지역이 같은 광역시/도인지 간단히 판단
    is_same_region = user_region.split()[0] in announcement_region

    return {
        **result,
        "user_region": user_region,
        "announcement_region": announcement_region,
        "is_same_region": is_same_region,
    }


# ── Tool 7: 청약 시점 적합성 분석 ────────────────────────────────

@tool
def analyze_subscription_timing(
    bankbook_type: str,
    bankbook_payments: int,
    bankbook_join_date: str,
    is_regulated: bool,
    supply_type: str,
) -> dict:
    """
    청약통장 정보와 공고 조건을 바탕으로 현재 청약 시점이 적합한지 분석합니다.

    Args:
        bankbook_type: 청약통장 종류 (예: "주택청약종합저축")
        bankbook_payments: 납입 횟수
        bankbook_join_date: 가입일 (예: "2020-01-01")
        is_regulated: 규제지역 여부
        supply_type: 공급 유형 ("민간" | "공공")

    Returns:
        dict: {
            "found": 정보 검색 성공 여부,
            "answer": 청약 시점 분석 답변,
            "sources": 참고 출처 목록,
            "is_ready": 1순위 자격 충족 여부 (간단 판단),
        }
    """
    area_type = "투기과열지구" if is_regulated else "일반지역"

    query = (
        f"{bankbook_type} 가입 후 납입 횟수 {bankbook_payments}회일 때 "
        f"{area_type} {supply_type}주택 청약 1순위 자격이 되는지? "
        f"가입기간 및 납입 횟수 요건을 알려줘."
    )

    system_prompt = (
        "당신은 대한민국 주택 청약 제도 전문가입니다. "
        "청약통장 종류와 납입 횟수, 지역 규제 여부를 고려해 "
        "현재 청약 신청이 가능한지, 1순위 자격을 갖췄는지 분석해주세요."
    )

    result = _rag_answer(query, system_prompt)

    # 간단한 1순위 자격 판단 (규제지역 24개월, 비규제 6개월 기준)
    required_payments = 24 if is_regulated else 6
    is_ready = bankbook_payments >= required_payments

    return {
        **result,
        "bankbook_type": bankbook_type,
        "bankbook_payments": bankbook_payments,
        "required_payments": required_payments,
        "is_ready": is_ready,
    }
