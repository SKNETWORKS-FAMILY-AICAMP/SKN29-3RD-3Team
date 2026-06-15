"""Runtime settings for Streamlit frontend API integration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from dotenv import load_dotenv
from pathlib import Path

# 최상위 폴더의 .env 로드
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

print("API URL:", os.getenv("CHEONGYAK_API_BASE_URL"))

@dataclass(frozen=True)
class FrontendSettings:
    api_mode: str
    api_base_url: str
    api_timeout_seconds: float


def _float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if not raw_value:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


@lru_cache(maxsize=1)
def load_settings() -> FrontendSettings:
    api_mode = os.getenv("CHEONGYAK_API_MODE", "auto").strip().lower()
    if api_mode not in {"auto", "mock", "http"}:
        api_mode = "auto"

    return FrontendSettings(
        api_mode=api_mode,
        api_base_url=os.getenv("CHEONGYAK_API_BASE_URL", "http://192.168.0.27:8000").rstrip("/"),
        api_timeout_seconds=_float_env("CHEONGYAK_API_TIMEOUT_SECONDS", 60.0),
    )
