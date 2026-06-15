from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SCORE_TABLE_PATH = (
    WORKSPACE_ROOT
    / "data"
    / "processed"
    / "structured"
    / "housing_subscription_score_tables.json"
)


class ScoreTableLoadError(RuntimeError):
    """Raised when the official structured score table cannot be loaded."""


@lru_cache(maxsize=1)
def load_housing_subscription_score_table() -> dict[str, Any]:
    """Load source-derived score tables.

    This intentionally has no silent fallback. The calculator should not produce
    scores if the official structured table is missing or malformed.
    """

    path = DEFAULT_SCORE_TABLE_PATH
    if not path.exists():
        raise ScoreTableLoadError(f"score table file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScoreTableLoadError(f"invalid score table JSON: {path}") from exc

    _validate_score_table(data, path)
    return data


def get_primary_source_ref() -> str:
    table = load_housing_subscription_score_table()
    basis = table["basis"]
    return f"{basis['primary_source_id']}:{basis['source_section']}"


def _validate_score_table(data: dict[str, Any], path: Path) -> None:
    required_top_level = {"basis", "score_limits", "tables", "rules"}
    missing = required_top_level - data.keys()
    if missing:
        raise ScoreTableLoadError(
            f"score table missing keys {sorted(missing)}: {path}"
        )

    required_tables = {
        "homeless_period",
        "dependent_family",
        "subscription_period",
    }
    missing_tables = required_tables - data["tables"].keys()
    if missing_tables:
        raise ScoreTableLoadError(
            f"score table missing tables {sorted(missing_tables)}: {path}"
        )
