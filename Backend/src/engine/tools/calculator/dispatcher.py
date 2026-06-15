"""Dispatch deterministic calculator tools for Node 2 style workflows."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from src.engine.tools.housing_subscription_score_tool import (
    calculate_housing_subscription_score_tool,
)
from src.engine.tools.special_supply_tools import (
    calculate_multi_child_special_supply_tool,
    calculate_newlywed_special_supply_tool,
    check_first_home_special_supply_tool,
)


ToolPayload = Mapping[str, Any]
ToolRunner = Callable[[ToolPayload], dict[str, Any]]


GENERAL_SUPPLY_ALIASES = frozenset(
    {
        "GENERAL_SUPPLY",
        "general_supply",
        "general",
        "일반공급",
        "일반공급 가점제",
    }
)
NEWLYWED_SPECIAL_ALIASES = frozenset(
    {
        "NEWLYWED_SPECIAL",
        "newlywed",
        "newlywed_special",
        "newlywed_special_supply",
        "신혼부부",
        "신혼부부 특별공급",
    }
)
MULTI_CHILD_SPECIAL_ALIASES = frozenset(
    {
        "MULTI_CHILD_SPECIAL",
        "multi_child",
        "multi_child_special",
        "multi_child_special_supply",
        "다자녀",
        "다자녀 특별공급",
    }
)
FIRST_HOME_SPECIAL_ALIASES = frozenset(
    {
        "LIFETIME_FIRST_SPECIAL",
        "FIRST_HOME_SPECIAL",
        "first_home",
        "first_home_special",
        "first_home_special_supply",
        "생애최초",
        "생애최초 특별공급",
    }
)


@dataclass(frozen=True)
class CalculatorToolSpec:
    """Registry entry for a deterministic calculator tool."""

    name: str
    supply_type_aliases: frozenset[str]
    payload_key: str
    runner: ToolRunner


def _run_housing_subscription_score(payload: ToolPayload) -> dict[str, Any]:
    return calculate_housing_subscription_score_tool(**dict(payload))


def _run_newlywed_special_supply(payload: ToolPayload) -> dict[str, Any]:
    return calculate_newlywed_special_supply_tool(**dict(payload))


def _run_multi_child_special_supply(payload: ToolPayload) -> dict[str, Any]:
    return calculate_multi_child_special_supply_tool(**dict(payload))


def _run_first_home_special_supply(payload: ToolPayload) -> dict[str, Any]:
    return check_first_home_special_supply_tool(**dict(payload))


NODE2_CALCULATOR_TOOLS: tuple[CalculatorToolSpec, ...] = (
    CalculatorToolSpec(
        name="calculate_housing_subscription_score",
        supply_type_aliases=GENERAL_SUPPLY_ALIASES,
        payload_key="housing_subscription_score",
        runner=_run_housing_subscription_score,
    ),
    CalculatorToolSpec(
        name="calculate_newlywed_special_supply",
        supply_type_aliases=NEWLYWED_SPECIAL_ALIASES,
        payload_key="special_supply",
        runner=_run_newlywed_special_supply,
    ),
    CalculatorToolSpec(
        name="calculate_multi_child_special_supply",
        supply_type_aliases=MULTI_CHILD_SPECIAL_ALIASES,
        payload_key="special_supply",
        runner=_run_multi_child_special_supply,
    ),
    CalculatorToolSpec(
        name="check_first_home_special_supply",
        supply_type_aliases=FIRST_HOME_SPECIAL_ALIASES,
        payload_key="special_supply",
        runner=_run_first_home_special_supply,
    ),
)


def run_calculator_tools(
    tool_inputs: Mapping[str, ToolPayload],
    *,
    candidate_supply_types: Iterable[str] | None = None,
    registry: Iterable[CalculatorToolSpec] = NODE2_CALCULATOR_TOOLS,
) -> dict[str, Any]:
    """Run calculator tools selected by candidate supply types.

    ``tool_inputs`` is keyed by each tool spec's ``payload_key``. This keeps
    calculator selection separate from frontend/backend request schemas.
    """
    requested_supply_types = _normalize_supply_types(candidate_supply_types)
    results: dict[str, Any] = {}
    skipped: dict[str, str] = {}

    for spec in registry:
        if requested_supply_types and spec.supply_type_aliases.isdisjoint(
            requested_supply_types
        ):
            skipped[spec.name] = "candidate supply types do not require this tool"
            continue

        payload = tool_inputs.get(spec.payload_key)
        if payload is None:
            skipped[spec.name] = f"missing tool input: {spec.payload_key}"
            continue

        results[spec.name] = spec.runner(payload)

    return {
        "tool_results": results,
        "skipped_tools": skipped,
    }


def _normalize_supply_types(values: Iterable[str] | None) -> frozenset[str]:
    if values is None:
        return frozenset()
    return frozenset(str(value).strip() for value in values if str(value).strip())
