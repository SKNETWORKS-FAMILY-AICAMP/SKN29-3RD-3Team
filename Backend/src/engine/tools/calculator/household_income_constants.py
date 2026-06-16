from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_HOUSEHOLD_INCOME_PATH = (
    WORKSPACE_ROOT
    / "data"
    / "processed"
    / "structured"
    / "household_income_standard.json"
)


class HouseholdIncomeLoadError(RuntimeError):
    """Raised when the household income standard table cannot be loaded."""


@lru_cache(maxsize=1)
def load_household_income_standard() -> dict[str, Any]:
    path = DEFAULT_HOUSEHOLD_INCOME_PATH
    if not path.exists():
        raise HouseholdIncomeLoadError(f"household income standard file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HouseholdIncomeLoadError(f"invalid household income standard JSON: {path}") from exc

    if "household_size_100_percent" not in data:
        raise HouseholdIncomeLoadError(
            f"household income standard missing 'household_size_100_percent': {path}"
        )
    return data


def get_household_income_100_percent(num_household_members: int) -> int | None:
    """Return the 100% monthly income standard for a given household size."""
    if num_household_members < 1:
        return None

    table = load_household_income_standard()
    sizes: dict[str, int] = table["household_size_100_percent"]
    max_defined_size = max(int(k) for k in sizes.keys())

    if num_household_members <= max_defined_size:
        return sizes[str(num_household_members)]

    increment = table.get("over_8_increment")
    if increment is None:
        return sizes[str(max_defined_size)]

    extra_members = num_household_members - max_defined_size
    return sizes[str(max_defined_size)] + increment * extra_members