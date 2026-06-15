"""API client boundary for FastAPI and mock diagnosis clients."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Protocol
import streamlit as st
from config.settings import load_settings



class ApiClientError(RuntimeError):
    """Raised when the configured API client cannot return a response."""


class DiagnosisClient(Protocol):
    def diagnose(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return diagnosis response."""

    def detail(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return detail diagnosis response."""

    def chat(self, question: str) -> dict[str, Any]:
        """Return chat response."""


class FastApiDiagnosisClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def diagnose(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/api/profile", payload)

    def detail(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/api/v1/diagnose/detail", payload)

    def chat(self, question: str) -> dict[str, Any]:
        return self._post("/api/chat", {
            "question": question,
            "session_id": st.session_state.get("session_id")
        })

    def health(self) -> dict[str, Any]:
        return self._get("/health")

    def _get(self, path: str) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            method="GET",
            headers={"Accept": "application/json"},
        )
        return self._open(request)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        return self._open(request)

    def _open(self, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ApiClientError(f"HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ApiClientError(f"FastAPI 연결 실패: {exc.reason}") from exc
        except TimeoutError as exc:
            raise ApiClientError("FastAPI 요청 시간이 초과되었습니다.") from exc

        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError as exc:
            raise ApiClientError("FastAPI 응답이 JSON 형식이 아닙니다.") from exc

        if not isinstance(parsed, dict):
            raise ApiClientError("FastAPI 응답 최상위 타입은 object여야 합니다.")
        return parsed


def get_diagnosis_client() -> DiagnosisClient:
    settings = load_settings()
    return FastApiDiagnosisClient(settings.api_base_url, settings.api_timeout_seconds)
