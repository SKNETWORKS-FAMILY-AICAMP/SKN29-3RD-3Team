"""Node 3: 조건부 분기 노드

사용자의 공고문 시뮬레이션 여부(wants_detailed_diagnosis)를 기반으로
Node 4(공고문 입력) 또는 Node 6(간단 리포트)으로 분기합니다.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal


def run_node3(state: Mapping[str, Any]) -> dict[str, Any]:
    """
    State를 그대로 유지하고 분기 정보만 반환합니다.
    실제 분기는 pipeline.py의 conditional_edges에서 처리합니다.
    """
    wants_detailed = state.get("wants_detailed_diagnosis", "아니오")
    return {"wants_detailed_diagnosis": wants_detailed}


def route_node3(state: Mapping[str, Any]) -> Literal["node4", "node6"]:
    """
    pipeline.py의 add_conditional_edges에서 사용할 라우터 함수입니다.

    Returns:
        "node4": 공고문 시뮬레이션 O → Node 4로 이동
        "node6": 공고문 시뮬레이션 X → Node 6으로 이동
    """
    wants_detailed = state.get("wants_detailed_diagnosis", "아니오")

    if wants_detailed in {"예", "yes", True, "true"}:
        return "node4"
    return "node6"