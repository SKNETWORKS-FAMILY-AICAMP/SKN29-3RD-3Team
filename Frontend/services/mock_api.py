"""Mock diagnosis and chat responses before backend integration."""

from __future__ import annotations

from typing import Any


class MockDiagnosisClient:
    def diagnose(self, payload: dict[str, Any]) -> dict[str, Any]:
        profile = payload.get("profile", {})
        blocked_reasons: list[str] = []
        candidate_supply_types: list[dict[str, Any]] = []
        marital_status = payload.get("marital_status")
        child_status = payload.get("child_status")
        detail = payload.get("detail", {}) if isinstance(payload.get("detail"), dict) else {}

        if not profile.get("is_homeless"):
            blocked_reasons.append("무주택 요건이 필요한 특별공급에서는 가능성이 낮을 수 있습니다.")

        candidate_supply_types.append(
            {
                "supply_type": "일반공급",
                "status": "추가 확인 필요",
                "reasons": [
                    f"{profile.get('bankbook_type', '청약통장')} 보유 정보가 입력되었습니다.",
                    "가입 기간, 납입 횟수, 예치금을 기준으로 지역별 1순위 요건 확인이 필요합니다.",
                ],
                "missing_checks": ["지역별 예치금 기준", "청약통장 가입 기간 기준"],
                "next_questions": ["notice_region", "housing_area"],
                "source_refs": ["청약홈", "입주자모집공고문"],
            }
        )

        if marital_status in {"MARRIED", "ENGAGED"} and profile.get("is_homeless"):
            candidate_supply_types.append(
                {
                    "supply_type": "신혼부부 특별공급",
                    "status": "추가 확인 필요",
                    "reasons": ["혼인 또는 결혼 예정 상태이며 무주택으로 입력되었습니다."],
                    "missing_checks": ["혼인기간", "소득 기준", "모집공고별 세부 기준"],
                    "next_questions": ["marriage_period", "average_monthly_income"],
                    "source_refs": ["청약홈 특별공급", "주택공급에 관한 규칙"],
                }
            )
        else:
            candidate_supply_types.append(
                {
                    "supply_type": "신혼부부 특별공급",
                    "status": "가능성 낮음",
                    "reasons": ["혼인 또는 결혼 예정 상태로 입력되지 않았거나 무주택 조건 확인이 필요합니다."],
                    "missing_checks": [],
                    "next_questions": [],
                    "source_refs": ["청약홈 특별공급"],
                }
            )

        if profile.get("minor_children_status") == "TWO_OR_MORE":
            candidate_supply_types.append(
                {
                    "supply_type": "다자녀 특별공급",
                    "status": "추가 확인 필요",
                    "reasons": ["만 19세 미만 자녀가 2명 이상인 범주로 입력되었습니다."],
                    "missing_checks": ["미성년 자녀 수 세부 기준", "소득·자산 기준", "모집공고별 배점 기준"],
                    "next_questions": ["average_monthly_income", "total_assets"],
                    "source_refs": ["청약홈 특별공급", "입주자모집공고문"],
                }
            )
        else:
            candidate_supply_types.append(
                {
                    "supply_type": "다자녀 특별공급",
                    "status": "가능성 낮음",
                    "reasons": ["미성년 자녀 2명 이상으로 입력되지 않았습니다."],
                    "missing_checks": [],
                    "next_questions": [],
                    "source_refs": ["청약홈 특별공급"],
                }
            )

        first_home_questions = []
        if profile.get("has_property_history") is None:
            first_home_questions.append("has_property_history")
        if profile.get("average_monthly_income") is None:
            first_home_questions.append("average_monthly_income")
        if profile.get("total_assets") is None:
            first_home_questions.append("total_assets")
        candidate_supply_types.append(
            {
                "supply_type": "생애최초 특별공급",
                "status": "추가 확인 필요" if first_home_questions else "가능성 있음",
                "reasons": ["무주택으로 입력되어 생애최초 특별공급 후보로 검토할 수 있습니다."]
                if profile.get("is_homeless")
                else ["현재 무주택으로 입력되지 않아 생애최초 특별공급 가능성이 낮습니다."],
                "missing_checks": ["과거 주택 소유 이력", "소득 기준", "자산 기준"],
                "next_questions": first_home_questions,
                "source_refs": ["청약홈 특별공급", "주택공급에 관한 규칙"],
            }
        )

        newborn_questions = []
        if child_status == "HAS_CHILD":
            newborn_questions.append("youngest_child_age_group")
        if profile.get("average_monthly_income") is None:
            newborn_questions.append("average_monthly_income")
        if profile.get("total_assets") is None:
            newborn_questions.append("total_assets")
        candidate_supply_types.append(
            {
                "supply_type": "신생아 특별공급",
                "status": "추가 확인 필요" if child_status == "HAS_CHILD" else "가능성 낮음",
                "reasons": ["자녀가 있고 무주택으로 입력되어 신생아 특별공급 후보 여부를 추가 확인할 수 있습니다."]
                if child_status == "HAS_CHILD"
                else ["자녀가 없는 것으로 입력되었습니다."],
                "missing_checks": ["가장 어린 자녀 연령", "소득 기준", "자산 기준"],
                "next_questions": newborn_questions if child_status == "HAS_CHILD" else [],
                "source_refs": ["청약홈 특별공급", "입주자모집공고문"],
            }
        )

        candidate_supply_types.extend(
            [
                {
                    "supply_type": "노부모부양 특별공급",
                    "status": "추가 확인 필요",
                    "reasons": ["노부모부양 여부는 추가 유형 확인에서 다룹니다."],
                    "missing_checks": ["노부모 부양 여부"],
                    "next_questions": ["elderly_support"],
                    "source_refs": ["청약홈 특별공급", "주택공급에 관한 규칙"],
                },
                {
                    "supply_type": "기관추천 특별공급",
                    "status": "추가 확인 필요",
                    "reasons": ["기관추천 특별공급은 추천기관 자격 확인이 필요합니다."],
                    "missing_checks": ["특수 신분 여부", "추천기관 자격 확인"],
                    "next_questions": ["special_identity_types"],
                    "source_refs": ["청약홈 특별공급", "입주자모집공고문"],
                },
            ]
        )

        missing_inputs = []
        if profile.get("average_monthly_income") is None:
            missing_inputs.append("가구 월평균 소득")
        if profile.get("total_assets") is None:
            missing_inputs.append("총자산")
        if profile.get("has_property_history") is None:
            missing_inputs.append("과거 주택 구입/소유 이력")

        resolved_detail_labels = _resolved_detail_labels(detail)
        for item in candidate_supply_types:
            item["missing_checks"] = [
                check
                for check in item.get("missing_checks", [])
                if check not in resolved_detail_labels
            ]
            item["next_questions"] = []
        pending_external_checks = _dedupe(
            [
                check
                for item in candidate_supply_types
                for check in item.get("missing_checks", [])
            ]
            + missing_inputs
        )

        return {
            "result_mode": "INITIAL_RESULT",
            "result_status": "추가 확인 필요" if pending_external_checks or blocked_reasons else "가능성 있음",
            "candidate_supply_types": candidate_supply_types,
            "blocked_reasons": blocked_reasons,
            "missing_inputs": missing_inputs,
            "next_questions": [],
            "next_actions": [
                "입력값으로 1차 후보를 확인했습니다. 남은 항목은 모집공고문 또는 증빙자료 기준으로 확인하세요.",
                "관심 모집공고의 지역별 예치금 기준 확인",
                "최종 신청 전에는 반드시 청약홈과 입주자모집공고문을 확인하세요.",
            ],
            "guide_message": "mock 응답입니다. 최종 자격은 청약홈과 모집공고문 기준으로 확인해야 합니다.",
            "warnings": ["FastAPI 연결 전 임시 진단 결과입니다."],
            "input_collection_mode": "INITIAL_WITH_DETAIL",
            "collected_detail_fields": _collect_detail_fields(detail),
            "pending_external_checks": pending_external_checks,
        }
    def detail(self, payload: dict[str, Any]) -> dict[str, Any]:
        answered = [key for key, value in payload.items() if value is not None]
        if answered:
            reasons = [f"{key} 상세값이 입력되었습니다." for key in answered]
            next_questions: list[str] = []
            status = "가능성 있음"
        else:
            reasons = []
            next_questions = [
                "marriage_period",
                "youngest_child_age_group",
                "child_count_group",
                "housing_history",
                "elderly_support",
            ]
            status = "추가 확인 필요"

        return {
            "result_mode": "INITIAL_RESULT" if answered else "NEEDS_DETAIL",
            "result_status": status,
            "candidate_supply_types": [
                {
                    "supply_type": "상세 확인",
                    "status": status,
                    "reasons": reasons,
                    "missing_checks": next_questions,
                    "next_questions": next_questions,
                    "source_refs": ["입주자모집공고문", "주택공급에 관한 규칙"],
                }
            ],
            "blocked_reasons": [],
            "missing_inputs": [],
            "next_questions": next_questions,
            "next_actions": ["입력값을 기준으로 후보 유형을 더 구체화합니다."],
            "guide_message": "mock 상세 진단 결과입니다.",
            "warnings": ["FastAPI 연결 전 임시 상세 진단 결과입니다."],
        }

    def chat(self, question: str, session_id: str | None = None) -> dict[str, Any]:
        return {
            "answer": (
                "현재는 mock 답변입니다. 필수 조건은 통장 정보, 무주택 여부와 기간, "
                "세대주 여부와 세대원 수, 출생 연도, 만 19세 미만 자녀 수 범주입니다."
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

def _resolved_detail_labels(detail: dict[str, Any]) -> set[str]:
    labels = {
        "marriage_period": "혼인기간",
        "youngest_child_age_group": "가장 어린 자녀 연령",
        "child_count_group": "미성년 자녀 수",
        "housing_history": "과거 주택 소유 이력",
        "elderly_support": "노부모 부양 여부",
    }
    return {
        label
        for key, label in labels.items()
        if detail.get(key) is not None and detail.get(key) != "UNKNOWN"
    }
