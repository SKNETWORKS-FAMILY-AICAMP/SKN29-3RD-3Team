"""
청약 RAG LangGraph 체인
────────────────────────────────────────────────────────────────
사용법:
    from rag_graph import build_graph

    app = build_graph()
    result = app.invoke({"question": "신혼부부 특별공급 소득 기준이 뭐야?"})
    print(result["answer"])
    print(result["sources"])

그래프 흐름:

    START
      │
      ▼
  classify_query  ── 질문을 3가지로 분류
      │              - "cheongyak"    : 청약 제도 관련 구체 질문
      │              - "general"      : 청약 일반 정의/개념 질문
      │              - "out_of_scope" : 세금/소송 등 데이터 범위 밖
      │
      ├─ cheongyak ──► retrieve ──► check_distance
      │                                   │
      │                         ┌─────────┴─────────┐
      │                         ▼ (가까움, <0.55)     ▼ (멈, >=0.55)
      │                   generate_rag           no_context
      │                         │                     │
      ├─ general ────────► general_answer            │
      │                         │                     │
      └─ out_of_scope ──► out_of_scope_answer         │
                                 │                     │
                                 └──────┬──────────────┘
                                        ▼
                                       END
────────────────────────────────────────────────────────────────
"""

import os
from typing import TypedDict, Literal
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from retriever import search, format_source

load_dotenv()

# ── 설정 ─────────────────────────────────────────────────────────

K_PER_COLLECTION = 3
TOP_K = 5

llm = ChatOpenAI(model="gpt-5.4-nano", temperature=0)
classifier_llm = ChatOpenAI(model="gpt-5.4-nano", temperature=0)


# ── State 정의 ──────────────────────────────────────────────────

class RAGState(TypedDict, total=False):
    question: str
    query_type: str            # "cheongyak" | "general" | "out_of_scope"
    retrieved: list            # [(dist, doc, meta, collection_name), ...]
    min_distance: float
    found: bool
    context: str
    sources: list[dict]        # [{"label": ..., "distance": ...}, ...]
    answer: str


# ── 1. classify_query ───────────────────────────────────────────

CLASSIFY_PROMPT = ChatPromptTemplate.from_template(
    """다음 사용자 질문을 아래 3가지 중 하나로 분류하세요.

- cheongyak: 한국 주택청약 제도의 구체적인 규정, 자격조건, 소득기준, 가점, 특별공급, 전매제한 등 데이터베이스에서 찾을 수 있는 질문
- general: "청약이 뭐야", "청약통장이 뭐야" 같은 아주 기초적인 정의/개념 질문으로 일반 지식으로 답변 가능한 질문
- out_of_scope: 세금(양도소득세 등), 소송, 부동산 시세 전망, 법률 자문 등 본 데이터(주택공급에 관한 규칙, FAQ, 매뉴얼, LH가이드)의 범위를 벗어나는 질문

질문: {question}

분류 결과를 정확히 다음 단어 중 하나로만 답하세요: cheongyak, general, out_of_scope"""
)

_classify_chain = CLASSIFY_PROMPT | classifier_llm | StrOutputParser()


def classify_query(state: RAGState) -> RAGState:
    raw = _classify_chain.invoke({"question": state["question"]}).strip().lower()

    if "out_of_scope" in raw:
        query_type = "out_of_scope"
    elif "general" in raw:
        query_type = "general"
    else:
        query_type = "cheongyak"

    return {**state, "query_type": query_type}


def route_after_classify(state: RAGState) -> Literal["retrieve", "general_answer", "out_of_scope_answer"]:
    if state["query_type"] == "general":
        return "general_answer"
    if state["query_type"] == "out_of_scope":
        return "out_of_scope_answer"
    return "retrieve"


# ── 2. retrieve ─────────────────────────────────────────────────

def retrieve(state: RAGState) -> RAGState:
    result = search(state["question"])

    results = result["results"]
    min_distance = result["min_distance"] if result["min_distance"] is not None else 999.0

    context_parts = []
    sources = []
    for dist, doc, meta, col_name in results:
        label = format_source(meta, col_name)
        context_parts.append(f"[출처: {label}]\n{doc}")
        sources.append({"label": label, "distance": round(dist, 4)})

    context = "\n\n---\n\n".join(context_parts)

    return {
        **state,
        "retrieved": results,
        "min_distance": min_distance,
        "context": context,
        "sources": sources,
        "found": result["found"],
    }

def route_after_retrieve(state: RAGState) -> Literal["generate_rag", "no_context"]:
    if state["found"]:
        return "generate_rag"
    return "no_context"


# ── 3. generate_rag ─────────────────────────────────────────────

RAG_PROMPT = ChatPromptTemplate.from_template(
    """당신은 대한민국 주택 청약 제도 전문가입니다.
아래 [Context]의 내용에만 기반하여 사용자의 질문에 정확하게 답변하세요.

규칙:
- 문서에 나와있지 않은 금액, 비율, 숫자, 기간을 임의로 가공하거나 지어내지 마세요.
- 소득 기준, 비율, 기간 등 수치 데이터가 있다면 표나 불릿 포인트로 정리하세요.
- 여러 출처에 상충되는 정보가 있다면 최신 자료(source_year가 큰 쪽)를 우선하세요.
- 각 출처는 [출처: ...] 형태로 Context에 표시되어 있습니다. 답변 본문에서 직접 [출처: ...]를 인용할 필요는 없습니다 (별도로 출처 목록이 제공됩니다).
- 출처는 출력에 들어가게 하지 마세요.
- Context에서 답을 찾을 수 없는 세부사항은 "제공된 자료에서는 확인할 수 없습니다"라고 명시하세요.
- 마크다운 헤더(#, ##)를 사용하지 마세요. 평문과 줄바꿈, 필요시 - 기호의 목록만 사용하세요.
- 답변 마지막에 추가 질문을 유도하는 멘트("원하시면 ~", "필요하시면 ~" 등)를 넣지 마세요.
- 대화는 일반 사용자와 대화한다고 생각하고 문서에 기반한 내용을 친절하게 가르쳐주세요.

[Context]
{context}

사용자 질문: {question}

전문가 답변:"""
)

_rag_chain = RAG_PROMPT | llm | StrOutputParser()


def generate_rag(state: RAGState) -> RAGState:
    answer = _rag_chain.invoke({
        "context": state["context"],
        "question": state["question"],
    })
    return {**state, "answer": answer}


# ── 4. general_answer (일반 정의 질문) ───────────────────────────

GENERAL_PROMPT = ChatPromptTemplate.from_template(
    """당신은 대한민국 주택 청약 제도 전문가입니다.
사용자가 청약과 관련된 기초적인 정의나 개념을 물어봤습니다.
일반적으로 알려진 정확한 정보를 바탕으로 간결하게 설명하세요.

- 세부 수치(소득기준, 가점 점수, 전매제한 기간 등)처럼 자주 바뀌는 정보는 "정확한 수치는 최신 입주자모집공고문이나 청약Home에서 확인하시는 것이 좋습니다"라고 안내하고, 임의의 숫자를 단정적으로 제시하지 마세요.
- 마크다운 헤더(#, ##)를 사용하지 말고 평문으로 답변하세요.
- 답변 마지막에 추가 질문을 유도하는 멘트는 넣지 마세요.
- 대화는 일반 사용자와 대화한다고 생각하고 문서에 기반한 내용을 친절하게 가르쳐주세요.

사용자 질문: {question}

답변:"""
)

_general_chain = GENERAL_PROMPT | llm | StrOutputParser()


def general_answer(state: RAGState) -> RAGState:
    answer = _general_chain.invoke({"question": state["question"]})
    return {**state, "answer": answer, "sources": []}


# ── 5. out_of_scope_answer ───────────────────────────────────────

def out_of_scope_answer(state: RAGState) -> RAGState:
    answer = (
        "죄송합니다. 이 질문은 현재 보유한 자료(주택공급에 관한 규칙, "
        "주택청약 FAQ, 업무매뉴얼, LH 분양가이드, 청약Home 안내)의 범위를 "
        "벗어나는 내용입니다.\n\n"
        "세금(양도소득세 등)이나 법률 자문이 필요한 경우 세무사 또는 "
        "법무사 등 전문가와 상담하시는 것을 권장합니다."
    )
    return {**state, "answer": answer, "sources": []}


# ── 6. no_context (검색 결과가 너무 멀 때) ────────────────────────

def no_context(state: RAGState) -> RAGState:
    answer = (
        "죄송합니다. 질문과 관련된 정확한 정보를 자료에서 찾지 못했습니다.\n\n"
        "질문을 더 구체적으로 작성해 주시거나, 청약Home(applyhome.co.kr) "
        "또는 마이홈포털(myhome.go.kr)에서 직접 확인해 보시기 바랍니다."
    )
    sources = [
        {"label": s["label"], "distance": s["distance"]}
        for s in state.get("sources", [])
    ]
    return {**state, "answer": answer, "sources": sources}


# ── 그래프 빌드 ───────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(RAGState)

    graph.add_node("classify_query", classify_query)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate_rag", generate_rag)
    graph.add_node("general_answer", general_answer)
    graph.add_node("out_of_scope_answer", out_of_scope_answer)
    graph.add_node("no_context", no_context)

    graph.set_entry_point("classify_query")

    graph.add_conditional_edges(
        "classify_query",
        route_after_classify,
        {
            "retrieve": "retrieve",
            "general_answer": "general_answer",
            "out_of_scope_answer": "out_of_scope_answer",
        },
    )

    graph.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {
            "generate_rag": "generate_rag",
            "no_context": "no_context",
        },
    )

    graph.add_edge("generate_rag", END)
    graph.add_edge("general_answer", END)
    graph.add_edge("out_of_scope_answer", END)
    graph.add_edge("no_context", END)

    return graph.compile()


# ── CLI 테스트 ───────────────────────────────────────────────────

if __name__ == "__main__":
    app = build_graph()

    test_questions = [
        "청약 가점제에서 미혼 자녀와 기혼 자녀의 부양가족 인정 기준 차이가 뭐야?",
        "공공분양 청약 시 자동차 자산은 어떻게 산정돼?",
        "신혼부부 특별공급에서 예비신혼부부의 혼인 증명 기한은 언제까지야?",
        "청약 당첨 후 입주까지 중도금 납부는 몇 회로 나눠서 내?",
        "투기과열지구에서 1순위 청약 자격을 갖추려면 가입기간이 얼마나 필요해?",
        "공공주택 특별공급 중 생애최초 공급 시 소득기준이 어떻게 돼?",
        "전매제한 기간 중 이혼으로 인한 재산분할은 전매 예외로 인정돼?",
        "거주의무 부여 주택에서 부기등기가 말소되지 않으면 어떻게 돼?",
        "청약 신청 시 형제자매도 부양가족으로 인정받을 수 있어?",
        "다자녀가구 특별공급에서 입양한 자녀도 자녀 수에 포함돼?",
    ]

    for q in test_questions:
        print("=" * 70)
        print(f"질문: {q}")
        print("=" * 70)

        result = app.invoke({"question": q})

        print(f"분류: {result['query_type']}")
        if result.get("min_distance") is not None and result["query_type"] == "cheongyak":
            print(f"최소 거리: {result['min_distance']:.4f}")

        print(f"\n컨텍스트:\n{result.get('context', '')}")
        print(f"\n답변:\n{result['answer']}")

        if result.get("sources"):
            print("\n출처:")
            for s in result["sources"]:
                print(f"  - {s['label']} (거리: {s['distance']})")
        print()
