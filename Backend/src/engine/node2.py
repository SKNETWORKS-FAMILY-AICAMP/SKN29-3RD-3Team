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

SUPPLY_TYPE_ALIASES = {
    "NEWLYWED_SPECIAL": "신혼부부 특공",
    "newlywed": "신혼부부 특공",
    "newlywed_special": "신혼부부 특공",
    "신혼부부 특별공급": "신혼부부 특공",
    "신혼부부 특공": "신혼부부 특공",
    "MULTI_CHILD_SPECIAL": "다자녀 특공",
    "multi_child": "다자녀 특공",
    "multi_child_special": "다자녀 특공",
    "다자녀 특별공급": "다자녀 특공",
    "다자녀 특공": "다자녀 특공",
    "LIFETIME_FIRST_SPECIAL": "생애최초 특공",
    "FIRST_HOME_SPECIAL": "생애최초 특공",
    "first_home": "생애최초 특공",
    "first_home_special": "생애최초 특공",
    "생애최초 특별공급": "생애최초 특공",
    "생애최초 특공": "생애최초 특공",
}

SUPPLY_METHOD_BY_TYPE = {
    "신혼부부 특공": "가점제",
    "다자녀 특공": "가점제",
    "생애최초 특공": "추첨제",
}


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

    return {
        "recommended_supply": _recommend_supply(available_supplies),
        "supply_analysis": {
            "available_supplies": available_supplies,
            "general_supply_score": general_supply_score,
            "general_max_score": general_max_score,
        },
    }


def _available_supply_types(state: Mapping[str, Any]) -> list[str]:
    raw_values = (
        state.get("available_supply_types")
        or state.get("node1_available_supply_types")
        or []
    )
    return [_canonical_supply_type(value) for value in raw_values]


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


def _recommend_supply(available_supplies: list[dict[str, Any]]) -> str:
    scored_supplies = [
        supply
        for supply in available_supplies
        if isinstance(supply.get("score"), int)
        and isinstance(supply.get("max_score"), int)
        and supply["max_score"] > 0
    ]
    if scored_supplies:
        return max(
            scored_supplies,
            key=lambda supply: supply["score"] / supply["max_score"],
        )["type"]
    if available_supplies:
        return available_supplies[0]["type"]
    return "일반공급"


def _canonical_supply_type(value: Any) -> str:
    text = str(value).strip()
    return SUPPLY_TYPE_ALIASES.get(text, text)


def _as_int(value: Any, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    return default
