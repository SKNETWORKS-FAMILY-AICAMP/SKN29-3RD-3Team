"""Top-level entrypoint for the general-supply score calculator tool."""

from __future__ import annotations

from typing import Any

from src.engine.tools.calculator.housing_subscription_score import (
    HousingSubscriptionScoreInput,
    calculate_housing_subscription_score,
)


TOOL_NAME = "calculate_housing_subscription_score"
TOOL_DESCRIPTION = (
    "Calculate the Korean general-supply housing subscription score from "
    "deterministic source-derived score tables. This tool does not query VectorDB."
)


def calculate_housing_subscription_score_tool(**kwargs: Any) -> dict[str, Any]:
    """Dictionary-returning wrapper for agent tool calls."""
    result = calculate_housing_subscription_score(kwargs)
    return result.model_dump(mode="json")


def get_housing_subscription_score_structured_tool() -> Any:
    """Build a LangChain StructuredTool lazily."""
    try:
        from langchain_core.tools import StructuredTool
    except ImportError as exc:
        raise RuntimeError(
            "langchain_core is required to create the StructuredTool adapter"
        ) from exc

    return StructuredTool.from_function(
        func=calculate_housing_subscription_score_tool,
        name=TOOL_NAME,
        description=TOOL_DESCRIPTION,
        args_schema=HousingSubscriptionScoreInput,
    )


__all__ = [
    "TOOL_DESCRIPTION",
    "TOOL_NAME",
    "calculate_housing_subscription_score_tool",
    "get_housing_subscription_score_structured_tool",
]
