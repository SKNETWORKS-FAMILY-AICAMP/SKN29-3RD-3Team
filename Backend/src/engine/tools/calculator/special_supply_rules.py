from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SPECIAL_SUPPLY_RULES_PATH = (
    WORKSPACE_ROOT
    / "data"
    / "processed"
    / "structured"
    / "special_supply_rules.json"
)


class SpecialSupplyRulesLoadError(RuntimeError):
    """Raised when the special-supply structured rule file cannot be loaded."""


@lru_cache(maxsize=1)
def load_special_supply_rules() -> dict[str, Any]:
    path = DEFAULT_SPECIAL_SUPPLY_RULES_PATH
    if not path.exists():
        raise SpecialSupplyRulesLoadError(f"special supply rules file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SpecialSupplyRulesLoadError(f"invalid special supply rules JSON: {path}") from exc

    _validate_special_supply_rules(data, path)
    return data


def _validate_special_supply_rules(data: dict[str, Any], path: Path) -> None:
    required_top_level = {"schema_version", "basis", "supply_types"}
    missing = required_top_level - data.keys()
    if missing:
        raise SpecialSupplyRulesLoadError(
            f"special supply rules missing keys {sorted(missing)}: {path}"
        )

    required_supply_types = {
        "newlywed",
        "multi_child",
        "first_home",
        "newborn",
        "elderly_parent",
    }
    actual_supply_types = set(data["supply_types"])
    missing_supply_types = required_supply_types - actual_supply_types
    if missing_supply_types:
        raise SpecialSupplyRulesLoadError(
            f"special supply rules missing supply types {sorted(missing_supply_types)}: {path}"
        )

    if "institution_recommended" in actual_supply_types:
        raise SpecialSupplyRulesLoadError(
            "institution_recommended must not be included in this MVP rule file"
        )
