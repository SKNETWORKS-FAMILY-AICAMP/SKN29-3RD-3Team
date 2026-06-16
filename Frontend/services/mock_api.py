"""Mock diagnosis and chat responses before backend integration."""

from __future__ import annotations

from typing import Any


class MockDiagnosisClient:
    def diagnose(self, payload: dict[str, Any]) -> dict[str, Any]:
        profile = payload.get("profile", {})
        blocked_reasons: list[str] = []
        candidate_supply_types: list[dict[str, Any]] = []
        marital_status = profile.get("marital_status") or payload.get("marital_status")
        child_status = profile.get("child_status") or payload.get("child_status")
        detail = payload.get("detail", {}) if isinstance(payload.get("detail"), dict) else {}

        if not profile.get("is_homeless"):
            blocked_reasons.append("무주택 요건이 필요한 특별공급에서는 가능성이 낮을 수 있습니다.")

        candidate_supply_types.append(
            {
                "supply_type": "일반공급",
                "status": "추가 확인 필요",
                "reasons": [
                    f"{profile.get('bankbook_type', '청약통장')} 정보가 입력되었습니다.",
                    "가입 기간, 납입 횟수, 예치금 기준 확인이 필요합니다.",
                ],
                "missing_checks": ["지역별 예치금 기준", "청약통장 가입 기간 기준"],
                "next_questions": [],
                "source_refs": ["청약홈", "입주자모집공고문"],
            }
        )

        candidate_supply_types.append(
            {
                "supply_type": "신혼부부 특별공급",
                "status": "검토 가능" if marital_status in {"MARRIED", "ENGAGED"} else "가능성 낮음",
                "reasons": ["혼인 상태와 소득 기준을 함께 확인해야 합니다."],
                "missing_checks": ["혼인기간", "소득 기준", "공고별 세대 기준"],
                "next_questions": [],
                "source_refs": ["주택공급에 관한 규칙"],
            }
        )

        candidate_supply_types.append(
            {
                "supply_type": "다자녀 특별공급",
                "status": "검토 가능" if profile.get("minor_child_count", 0) >= 2 else "가능성 낮음",
                "reasons": ["미성년 자녀 수를 기준으로 후보 여부를 판단합니다."],
                "missing_checks": ["미성년 자녀 수", "소득/자산 기준"],
                "next_questions": [],
                "source_refs": ["입주자모집공고문"],
            }
        )

        candidate_supply_types.append(
            {
                "supply_type": "생애최초 특별공급",
                "status": "검토 가능" if not profile.get("has_property_history") else "가능성 낮음",
                "reasons": ["주택 구입/소유 이력, 소득, 자산 기준을 함께 봅니다."],
                "missing_checks": ["과거 주택 소유 이력", "소득 기준", "자산 기준"],
                "next_questions": [],
                "source_refs": ["주택공급에 관한 규칙"],
            }
        )

        if child_status == "HAS_CHILD":
            candidate_supply_types.append(
                {
                    "supply_type": "신생아 특별공급",
                    "status": "추가 확인 필요",
                    "reasons": ["가장 어린 자녀 연령에 따라 후보 여부가 달라집니다."],
                    "missing_checks": ["가장 어린 자녀 연령"],
                    "next_questions": [],
                    "source_refs": ["입주자모집공고문"],
                }
            )

        pending_external_checks = _dedupe(
            [
                check
                for item in candidate_supply_types
                for check in item.get("missing_checks", [])
            ]
        )

        return {
            "result_mode": "INITIAL_RESULT",
            "result_status": "추가 확인 필요" if pending_external_checks or blocked_reasons else "가능성 있음",
            "candidate_supply_types": candidate_supply_types,
            "blocked_reasons": blocked_reasons,
            "missing_inputs": [],
            "next_questions": [],
            "next_actions": [
                "입력값 기준 1차 후보를 확인했습니다.",
                "최종 신청 전 청약홈과 입주자모집공고문 기준을 확인하세요.",
            ],
            "guide_message": "mock 응답입니다. FastAPI 연결 상태를 확인해 주세요.",
            "warnings": ["FastAPI 연결 실패 시 표시되는 임시 진단 결과입니다."],
            "input_collection_mode": "INITIAL_WITH_DETAIL",
            "collected_detail_fields": _collect_detail_fields(detail),
            "pending_external_checks": pending_external_checks,
        }

    def detail(self, payload: dict[str, Any]) -> dict[str, Any]:
        answered = [key for key, value in payload.items() if value is not None]
        return {
            "result_mode": "INITIAL_RESULT" if answered else "NEEDS_DETAIL",
            "result_status": "가능성 있음" if answered else "추가 확인 필요",
            "candidate_supply_types": [],
            "blocked_reasons": [],
            "missing_inputs": [],
            "next_questions": [],
            "next_actions": ["입력값을 기준으로 후보 유형을 구체화합니다."],
            "guide_message": "mock 상세 진단 결과입니다.",
            "warnings": ["FastAPI 연결 실패 시 표시되는 임시 상세 진단 결과입니다."],
        }

    def simulate(self, session_id: str, simulate: bool) -> dict[str, Any]:
        if simulate:
            return {
                "result_mode": "ANNOUNCEMENT_FLOW",
                "result_status": "waiting",
                "candidate_supply_types": [],
                "blocked_reasons": [],
                "missing_inputs": [],
                "next_questions": [],
                "next_actions": [],
                "guide_message": "공고문 정보를 입력해 주세요.",
                "warnings": [],
                "session_id": session_id,
                "backend_status": "waiting",
            }
        return {
            "result_mode": "ANNOUNCEMENT_FLOW",
            "result_status": "success",
            "candidate_supply_types": [],
            "blocked_reasons": [],
            "missing_inputs": [],
            "next_questions": [],
            "next_actions": ["공고문 기준 세부 조건은 별도로 확인하세요."],
            "guide_message": "공고문 없이 생성한 mock 리포트입니다.",
            "warnings": [],
            "session_id": session_id,
            "report": {
                "summary": "공고문 없이 생성한 mock 리포트입니다.",
                "next_steps": ["공고문 기준 세부 조건은 별도로 확인하세요."],
            },
            "backend_status": "success",
        }

    def announcement(self, session_id: str, announcement_text: str) -> dict[str, Any]:
        return {
            "result_mode": "ANNOUNCEMENT_FLOW",
            "result_status": "success",
            "candidate_supply_types": [],
            "blocked_reasons": [],
            "missing_inputs": [],
            "next_questions": [],
            "next_actions": ["백엔드 연결 후 Node4 구조화 결과를 확인하세요."],
            "guide_message": "공고문 줄글 입력을 받은 mock 리포트입니다.",
            "warnings": [],
            "session_id": session_id,
            "report": {
                "summary": "공고문 줄글 입력을 받은 mock 리포트입니다.",
                "announcement_text": announcement_text,
                "next_steps": ["백엔드 연결 후 Node4 구조화 결과를 확인하세요."],
            },
            "backend_status": "success",
        }

    def chat(self, question: str, session_id: str | None = None) -> dict[str, Any]:
        return {
            "answer": (
                "현재는 mock 응답입니다. 필수 조건은 통장 정보, 무주택 여부와 기간, "
                "세대주 여부와 세대원 수, 혼인/자녀, 소득/자산 정보입니다."
            ),
            "question": question,
            "session_id": session_id or "mock-session",
            "sources": ["청약홈", "주택공급에 관한 규칙"],
            "source_refs": ["청약홈", "주택공급에 관한 규칙"],
        }


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _collect_detail_fields(detail: dict[str, Any]) -> list[str]:
    labels = {
        "marriage_period": "혼인기간",
        "youngest_child_age_group": "가장 어린 자녀 연령",
        "child_count_group": "미성년 자녀 수",
        "housing_history": "과거 주택 소유 이력",
        "elderly_support": "노부모 부양 여부",
    }
    return [label for key, label in labels.items() if detail.get(key) is not None]
