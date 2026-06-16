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
    general_score_breakdown = _build_general_score_breakdown(general_result)

    supply_rank = _build_supply_rank(
        available_supplies,
        general_supply_score,
        general_max_score,
        general_score_breakdown,
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

def _build_general_score_breakdown(general_result: Mapping[str, Any]) -> dict[str, int]:
    breakdown: dict[str, int] = {}
    for key in ("homeless_score", "dependent_family_score", "subscription_score", "spouse_subscription_score"):
        value = general_result.get(key)
        if isinstance(value, int) and value > 0:
            breakdown[key] = value
    return breakdown

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
        "status": result.get("status"),
        "score_breakdown": result.get("score_breakdown", {}),
        "matched_items": result.get("matched_items", []),
        "missing_items": result.get("missing_items", []),
        "source_refs": result.get("source_refs", []),
    }


def _build_supply_rank(
    available_supplies: list[dict[str, Any]],
    general_supply_score: int,
    general_max_score: int,
    general_score_breakdown: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    scored = [
        s for s in available_supplies
        if s["method"] == "가점제"
        and isinstance(s.get("score"), int)
        and isinstance(s.get("max_score"), int)
        and s["max_score"] > 0
    ]
    lottery_all = [s for s in available_supplies if s["method"] == "추첨제"]
    lottery_eligible = [s for s in lottery_all if not s.get("missing_items")]
    lottery_unresolved = [s for s in lottery_all if s.get("missing_items")]

    scored_sorted = sorted(scored, key=lambda s: s["score"] / s["max_score"], reverse=True)
    best_ratio = scored_sorted[0]["score"] / scored_sorted[0]["max_score"] if scored_sorted else 0.0

    general_ratio = general_supply_score / general_max_score if general_max_score > 0 else 0.0

    def _lottery_entry(s: dict[str, Any], reason: str) -> dict[str, Any]:
        return {
            "type": s["type"],
            "score": None,
            "max_score": None,
            "ratio": None,
            "reason": reason,
            "method": "추첨제",
            "score_breakdown": s.get("score_breakdown", {}),
            "matched_items": s.get("matched_items", []),
            "missing_items": s.get("missing_items", []),
            "source_refs": s.get("source_refs", []),
        }

    def _scored_entry(s: dict[str, Any], reason: str) -> dict[str, Any]:
        ratio = s["score"] / s["max_score"]
        return {
            "type": s["type"],
            "score": s["score"],
            "max_score": s["max_score"],
            "ratio": f"{ratio:.0%}",
            "reason": reason,
            "method": "가점제",
            "score_breakdown": s.get("score_breakdown", {}),
            "matched_items": s.get("matched_items", []),
            "missing_items": s.get("missing_items", []),
            "source_refs": s.get("source_refs", []),
        }

    general_entry = {
        "type": "일반공급",
        "score": general_supply_score,
        "max_score": general_max_score,
        "ratio": f"{general_ratio:.0%}" if general_max_score > 0 else None,
        "reason": f"가점 {general_supply_score}/{general_max_score}점 ({general_ratio:.0%})" if general_max_score > 0 else "",
        "method": "가점제",
        "score_breakdown": general_score_breakdown or {},
        "matched_items": [],
        "missing_items": [],
        "source_refs": [],
    }

    confirmed_entries: list[dict[str, Any]] = []

    if not lottery_eligible and not scored_sorted:
        # 신청 가능 확정 특공이 없으면 일반공급을 최우선으로
        confirmed_entries.append(general_entry)
    elif lottery_eligible and best_ratio < COMPETITIVENESS_THRESHOLD:
        for s in lottery_eligible:
            confirmed_entries.append(_lottery_entry(s, "추첨제 우선 추천"))
        for s in scored_sorted:
            ratio = s["score"] / s["max_score"]
            confirmed_entries.append(
                _scored_entry(s, f"점수제 경쟁력({best_ratio:.0%}) 부족, 보조 전략으로 점수제 병행 가능")
            )
        confirmed_entries.append(general_entry)
    else:
        for s in scored_sorted:
            confirmed_entries.append(_scored_entry(s, f"점수 비율 {s['score']/s['max_score']:.0%}로 경쟁력 있음"))
        for s in lottery_eligible:
            confirmed_entries.append(_lottery_entry(s, "추첨제 동등 기회로 병행 고려"))
        confirmed_entries.append(general_entry)

    unresolved_entries = [
        _lottery_entry(
            s,
            f"기준 미달 항목 있음 ({', '.join(s.get('missing_items', []))}) — 확인 후 재검토 필요",
        )
        for s in lottery_unresolved
    ]

    rank = confirmed_entries + unresolved_entries
    for index, entry in enumerate(rank):
        entry["rank"] = index + 1
    return rank


def _as_int(value: Any, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    return default