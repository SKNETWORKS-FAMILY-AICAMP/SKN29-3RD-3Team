"""Top-level entrypoints for special-supply calculator tools."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.engine.tools.calculator.special_supply import (
    SpecialSupplyInput,
    calculate_multi_child_special_supply,
    calculate_newlywed_special_supply,
    check_first_home_special_supply,
)


NEWLYWED_TOOL_NAME = "calculate_newlywed_special_supply"
MULTI_CHILD_TOOL_NAME = "calculate_multi_child_special_supply"
FIRST_HOME_TOOL_NAME = "check_first_home_special_supply"


def calculate_newlywed_special_supply_tool(**kwargs: Any) -> dict[str, Any]:
    """Dictionary-returning wrapper for newlywed special-supply checks."""
    result = calculate_newlywed_special_supply(kwargs)
    return result.model_dump(mode="json")


def calculate_multi_child_special_supply_tool(**kwargs: Any) -> dict[str, Any]:
    """Dictionary-returning wrapper for multi-child special-supply checks."""
    result = calculate_multi_child_special_supply(kwargs)
    return result.model_dump(mode="json")


def check_first_home_special_supply_tool(**kwargs: Any) -> dict[str, Any]:
    """Dictionary-returning wrapper for first-home special-supply checks."""
    result = check_first_home_special_supply(kwargs)
    return result.model_dump(mode="json")


def get_newlywed_special_supply_structured_tool() -> Any:
    return _build_structured_tool(
        calculate_newlywed_special_supply_tool,
        NEWLYWED_TOOL_NAME,
        "Evaluate newlywed special-supply eligibility and score fields.",
    )


def get_multi_child_special_supply_structured_tool() -> Any:
    return _build_structured_tool(
        calculate_multi_child_special_supply_tool,
        MULTI_CHILD_TOOL_NAME,
        "Evaluate multi-child special-supply eligibility and score fields.",
    )


def get_first_home_special_supply_structured_tool() -> Any:
    return _build_structured_tool(
        check_first_home_special_supply_tool,
        FIRST_HOME_TOOL_NAME,
        "Evaluate first-home special-supply eligibility fields.",
    )


def _build_structured_tool(
    func: Callable[..., dict[str, Any]],
    name: str,
    description: str,
) -> Any:
    try:
        from langchain_core.tools import StructuredTool
    except ImportError as exc:
        raise RuntimeError(
            "langchain_core is required to create the StructuredTool adapter"
        ) from exc

    return StructuredTool.from_function(
        func=func,
        name=name,
        description=description,
        args_schema=SpecialSupplyInput,
    )


__all__ = [
    "FIRST_HOME_TOOL_NAME",
    "MULTI_CHILD_TOOL_NAME",
    "NEWLYWED_TOOL_NAME",
    "calculate_multi_child_special_supply_tool",
    "calculate_newlywed_special_supply_tool",
    "check_first_home_special_supply_tool",
    "get_first_home_special_supply_structured_tool",
    "get_multi_child_special_supply_structured_tool",
    "get_newlywed_special_supply_structured_tool",
]
