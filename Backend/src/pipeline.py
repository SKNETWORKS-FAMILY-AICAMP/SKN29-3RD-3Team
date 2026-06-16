"""
청약 전략 서비스 파이프라인
Node 1 → Node 2 → [인터럽트] → Node 3 → Node 4 → Node 5 → Node 6
"""

from __future__ import annotations

import uuid
from typing import Any
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.engine.node1 import run_node1
from src.engine.node2 import node2_recommend_supply
from src.engine.node3 import run_node3, route_node3
from src.engine.node4 import run_node4
from src.engine.node5 import run_node5
from src.engine.node6 import run_node6


# ── 파이프라인 State 정의 ─────────────────────────────────────────

class PipelineState(TypedDict, total=False):
    # 프로필
    profile: dict

    # Node 1 결과
    available_supply_types: list
    tool_inputs: dict
    node1_warnings: list

    # Node 2 결과
    supply_analysis: dict
    supply_rank: list
    recommended_supply: str

    # Node 3 분기
    wants_detailed_diagnosis: str

    # Node 4 결과
    announcement: dict

    # Node 5 결과
    loan_result: dict
    investment_result: dict
    risk_result: dict
    agent_result: str

    # Node 6 결과
    final_report: dict


# ── 메모리 저장소 ─────────────────────────────────────────────────
memory = MemorySaver()


# ── 파이프라인 그래프 빌드 ────────────────────────────────────────

def _build_pipeline():
    graph = StateGraph(PipelineState)

    graph.add_node("node1", run_node1)
    graph.add_node("node2", node2_recommend_supply)
    graph.add_node("node3", run_node3)
    graph.add_node("node4", run_node4)
    graph.add_node("node5", run_node5)
    graph.add_node("node6", run_node6)

    graph.add_edge(START, "node1")
    graph.add_edge("node1", "node2")
    graph.add_edge("node2", "node3")

    graph.add_conditional_edges(
        "node3",
        route_node3,
        {
            "node4": "node4",
            "node6": "node6",
        }
    )

    graph.add_edge("node4", "node5")
    graph.add_edge("node5", "node6")
    graph.add_edge("node6", END)

    return graph.compile(
        checkpointer=memory,
        interrupt_after=["node2"],
    )

pipeline = _build_pipeline()


# ── 외부 호출 함수 ────────────────────────────────────────────────

def run_pipeline_until_node2(profile: dict[str, Any]) -> dict[str, Any]:
    """Node 1~2 실행 후 인터럽트. supply_rank와 session_id 반환."""
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}
    initial_state = {"profile": profile}

    for event in pipeline.stream(initial_state, config, stream_mode="values"):
        print(f"[DEBUG] keys: {event.keys()}")
        print(f"[DEBUG] tool_inputs: {event.get('tool_inputs')}")
        print(f"[DEBUG] available_supply_types: {event.get('available_supply_types')}")

    state = pipeline.get_state(config)

    return {
        "session_id": session_id,
        "supply_rank": state.values.get("supply_rank", []),
        "recommended_supply": state.values.get("recommended_supply", "일반공급"),
    }


def resume_pipeline(session_id: str, simulate: bool) -> dict[str, Any]:
    """Node 2 인터럽트 해제. simulate O/X에 따라 분기."""
    config = {"configurable": {"thread_id": session_id}}

    pipeline.update_state(
        config,
        {"wants_detailed_diagnosis": "예" if simulate else "아니오"},
    )

    for _ in pipeline.stream(None, config, stream_mode="values"):
        pass

    state = pipeline.get_state(config)

    if state.next and "node4" in state.next:
        return {
            "status": "waiting",
            "session_id": session_id,
            "message": "공고문 정보를 입력해주세요.",
        }

    return {
        "status": "success",
        "session_id": session_id,
        "report": state.values.get("final_report", {}),
    }


def resume_with_announcement(session_id: str, announcement_text: str) -> dict[str, Any]:
    """Node 4 인터럽트 해제. 공고문 입력 후 Node 5~6 실행."""
    config = {"configurable": {"thread_id": session_id}}

    for _ in pipeline.stream(
        Command(resume=announcement_text),
        config,
        stream_mode="values"
    ):
        pass

    state = pipeline.get_state(config)

    return {
        "status": "success",
        "session_id": session_id,
        "report": state.values.get("final_report", {}),
    }