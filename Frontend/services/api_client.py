"""API client boundary for FastAPI and mock diagnosis clients."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Protocol

from config.settings import load_settings
from services.mock_api import MockDiagnosisClient


class ApiClientError(RuntimeError):
    """Raised when the configured API client cannot return a response."""


class DiagnosisClient(Protocol):
    def diagnose(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return diagnosis response."""

    def detail(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return detail diagnosis response."""

    def chat(self, question: str, session_id: str | None = None) -> dict[str, Any]:
        """Return chat response."""


class FastApiDiagnosisClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def diagnose(self, payload: dict[str, Any]) -> dict[str, Any]:
        return _normalize_profile_response(self._post("/api/profile", payload))

    def detail(self, payload: dict[str, Any]) -> dict[str, Any]:
        return _normalize_profile_response(self._post("/api/profile", payload))

    def chat(self, question: str, session_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"question": question}
        if session_id:
            payload["session_id"] = session_id
        return self._post("/api/chat", payload)

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
    if settings.api_mode in {"auto", "http"}:
        timeout_seconds = (
            min(settings.api_timeout_seconds, 3.0)
            if settings.api_mode == "auto"
            else settings.api_timeout_seconds
        )
        return FastApiDiagnosisClient(settings.api_base_url, timeout_seconds)
    return MockDiagnosisClient()


def check_api_connection() -> dict[str, Any]:
    """Return a lightweight API connection status for the Streamlit sidebar."""
    settings = load_settings()
    if settings.api_mode == "mock":
        return {
            "ok": True,
            "mode": "mock",
            "base_url": settings.api_base_url,
            "message": "Mock mode",
        }

    try:
        response = FastApiDiagnosisClient(
            settings.api_base_url,
            min(settings.api_timeout_seconds, 3.0),
        ).health()
    except ApiClientError as exc:
        message = str(exc)
        if settings.api_mode == "auto":
            message = f"{message} · mock 응답으로 UI 검증 가능"
        return {
            "ok": False,
            "mode": settings.api_mode,
            "base_url": settings.api_base_url,
            "message": message,
        }

    return {
        "ok": response.get("status") == "ok",
        "mode": settings.api_mode,
        "base_url": settings.api_base_url,
        "message": response.get("status", "unknown"),
    }


def _normalize_profile_response(response: dict[str, Any]) -> dict[str, Any]:
    """Adapt clean-branch /api/profile echo responses to the existing result UI."""
    if "candidate_supply_types" in response or response.get("result_mode"):
        return response

    if response.get("node1") or response.get("node2"):
        node2 = response.get("node2") or {}
        node3 = response.get("node3") or {}
        node6 = response.get("node6") or {}
        final_report = node6.get("final_report") or {}
        available_supplies = node2.get("ranked_supplies") or (
            (node2.get("supply_analysis") or {}).get("ranked_supplies")
            or (node2.get("supply_analysis") or {}).get("available_supplies")
            or []
        )

        return {
            "result_mode": "LANGGRAPH_PROFILE",
            "result_status": _profile_result_status(node3),
            "candidate_supply_types": [
                {
                    "supply_type": item.get("type"),
                    "status": "추천"
                    if item.get("type") == node2.get("recommended_supply")
                    else "검토 가능",
                    "reasons": [
                        f"순위: {item.get('rank', '-')}",
                        f"방식: {item.get('method')}",
                        _score_text(item),
                        str(item.get("reason") or ""),
                    ],
                    "missing_checks": [],
                    "next_questions": [],
                    "source_refs": [],
                }
                for item in available_supplies
            ],
            "blocked_reasons": [],
            "missing_inputs": node3.get("required_inputs", []) if node3.get("awaiting_input") else [],
            "next_questions": [],
            "next_actions": final_report.get("next_steps") or [],
            "guide_message": final_report.get("summary")
            or "LangGraph 진단 결과를 수신했습니다.",
            "warnings": final_report.get("warnings") or [],
            "profile": response.get("profile", {}),
            "node1": response.get("node1"),
            "node2": node2,
            "node3": node3,
            "node4": response.get("node4"),
            "node5": response.get("node5"),
            "node6": node6,
            "backend_status": response.get("status"),
        }

    profile = response.get("profile", {})
    return {
        "result_mode": "PROFILE_ACCEPTED",
        "result_status": "입력 수신 완료",
        "candidate_supply_types": [],
        "blocked_reasons": [],
        "missing_inputs": [],
        "next_questions": [],
        "next_actions": [
            "백엔드가 profile 입력을 정상 수신했습니다.",
            "profile 엔진 노드 연결 후 청약 유형별 진단 결과가 이 영역에 표시됩니다.",
        ],
        "guide_message": "현재 clean-branch의 /api/profile은 엔진 연결 전 수신 확인 응답입니다.",
        "warnings": [],
        "profile": profile,
        "node1": response.get("node1"),
        "node2": response.get("node2"),
        "node3": response.get("node3"),
        "node4": response.get("node4"),
        "node5": response.get("node5"),
        "node6": response.get("node6"),
        "backend_status": response.get("status"),
    }


def _score_text(item: dict[str, Any]) -> str:
    score = item.get("score")
    max_score = item.get("max_score")
    if score is None or max_score is None:
        return "점수: 추첨/별도 기준"
    return f"점수: {score}/{max_score}"


def _profile_result_status(node3: dict[str, Any]) -> str:
    route = node3.get("route")
    if route == "detailed":
        return "상세 진단 완료"
    if route == "awaiting_announcement":
        return "공고 정보 입력 필요"
    return "기본 진단 완료"
