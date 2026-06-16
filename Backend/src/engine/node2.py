"""Node 2 strategy recommendation.

Node 2 does not wire graph edges. It reads Node 1 state and returns only the
recommendation payload expected by the pipeline.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from src.engine.tools.calculator.dispatcher import run_calculator_tools


GENERAL_SUPPLY_TOOL = "calculate_housing_subscription_score"

SPECIAL_SUPPLY_TOOL_BY_TYPE = {
    "신혼부부 특공": "calculate_newlywed_special_supply",
    "다자녀 특공": "calculate_multi_child_special_supply",
    "생애최초 특공": "check_first_home_special_supply",
}

SUPPLY_METHOD_BY_TYPE = {
    "신혼부부 특공": "가점제",
    "다자녀 특공": "가점제",
    "생애최초 특공": "추첨제",
}

# 점수제 특공 경쟁력 기준 (Node 5 strategy_tools.py와 동일)
COMPETITIVENESS_THRESHOLD = 0.6


def node2_recommend_supply(state: Mapping[str, Any]) -> dict[str, Any]:
    """Build the Node 2 output payload from Node 1 state."""
    available_supply_types = _available_supply_types(state)
    tool_results = _tool_results(state, available_supply_types)
    available_supplies = [
        _build_supply_analysis_item(supply_type, tool_results)
        for supply_type in available_supply_types
    ]

    general_result = tool_results.get(GENERAL_SUPPLY_TOOL, {})
    general_supply_score = _as_int(general_result.get("total_score"), default=0)
    general_max_score = _as_int(general_result.get("max_score"), default=84)

    supply_rank = _build_supply_rank(
        available_supplies, general_supply_score, general_max_score
    )

    return {
        # ── State 업데이트용 (Node 5로 전달) ──────────────────────
        "recommended_supply": supply_rank[0]["type"] if supply_rank else "일반공급",
        "supply_analysis": {
            "available_supplies": available_supplies,
            "general_supply_score": general_supply_score,
            "general_max_score": general_max_score,
        },
        # ── 프론트 반환용 (FastAPI 인터럽트 시점에 꺼내서 반환) ────
        "supply_rank": supply_rank,
    }


def _available_supply_types(state: Mapping[str, Any]) -> list[str]:
    raw_values = state.get("available_supply_types") or []
    return list(raw_values)


def _tool_results(
    state: Mapping[str, Any],
    available_supply_types: Iterable[str],
) -> Mapping[str, Any]:
    direct_results = state.get("tool_results")
    if isinstance(direct_results, Mapping):
        return direct_results

    tool_inputs = state.get("tool_inputs")
    if not isinstance(tool_inputs, Mapping):
        return {}

    calculator_result = run_calculator_tools(
        tool_inputs,
        candidate_supply_types=available_supply_types,
    )

    print(f"[DEBUG] calculator_result: {calculator_result}")
    return calculator_result.get("tool_results", {})


def _build_supply_analysis_item(
    supply_type: str,
    tool_results: Mapping[str, Any],
) -> dict[str, Any]:
    tool_name = SPECIAL_SUPPLY_TOOL_BY_TYPE.get(supply_type)
    result = tool_results.get(tool_name, {}) if tool_name else {}
    method = SUPPLY_METHOD_BY_TYPE.get(supply_type, "추첨제")

    if method == "추첨제":
        score = None
        max_score = None
    else:
        score = result.get("score")
        max_score = result.get("max_score")

    return {
        "type": supply_type,
        "score": score,
        "max_score": max_score,
        "method": method,
    }


def _build_supply_rank(
    available_supplies: list[dict[str, Any]],
    general_supply_score: int,
    general_max_score: int,
) -> list[dict[str, Any]]:
    rank = []

    scored = [
        s for s in available_supplies
        if s["method"] == "가점제"
        and isinstance(s.get("score"), int)
        and isinstance(s.get("max_score"), int)
        and s["max_score"] > 0
    ]
    lottery = [s for s in available_supplies if s["method"] == "추첨제"]

    best_ratio = max(
        (s["score"] / s["max_score"] for s in scored),
        default=0.0,
    )

    if scored and best_ratio >= COMPETITIVENESS_THRESHOLD:
        best = max(scored, key=lambda s: s["score"] / s["max_score"])
        rank.append({
            "rank": 1,
            "type": best["type"],
            "score": best["score"],
            "max_score": best["max_score"],
            "ratio": f"{best_ratio:.0%}",
            "reason": f"점수 비율 {best_ratio:.0%}로 경쟁력 있음",
            "method": "가점제",
        })
        for s in lottery:
            rank.append({
                "rank": 2,
                "type": s["type"],
                "score": None,
                "max_score": None,
                "ratio": None,
                "reason": "추첨제 동등 기회로 병행 고려",
                "method": "추첨제",
            })
    else:
        for i, s in enumerate(lottery, 1):
            rank.append({
                "rank": i,
                "type": s["type"],
                "score": None,
                "max_score": None,
                "ratio": None,
                "reason": f"점수제 경쟁력({best_ratio:.0%}) 부족, 추첨제 우선 추천",
                "method": "추첨제",
            })
        if scored:
            best = max(scored, key=lambda s: s["score"] / s["max_score"])
            rank.append({
                "rank": len(lottery) + 1,
                "type": best["type"],
                "score": best["score"],
                "max_score": best["max_score"],
                "ratio": f"{best_ratio:.0%}",
                "reason": "보조 전략으로 점수제 병행 가능",
                "method": "가점제",
            })

    if general_max_score > 0:
        general_ratio = general_supply_score / general_max_score
        rank.append({
            "rank": len(rank) + 1,
            "type": "일반공급",
            "score": general_supply_score,
            "max_score": general_max_score,
            "ratio": f"{general_ratio:.0%}",
            "reason": f"가점 {general_supply_score}/{general_max_score}점 ({general_ratio:.0%})",
            "method": "가점제",
        })

    return rank


def _as_int(value: Any, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    return default