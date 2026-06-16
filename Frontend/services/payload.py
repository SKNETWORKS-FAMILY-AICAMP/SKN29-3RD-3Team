"""Payload conversion and validation for diagnosis inputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

DETAIL_PAYLOAD_FIELDS = (
    "marriage_period",
    "youngest_child_age_group",
    "child_count_group",
    "housing_history",
    "elderly_support",
)
REQUIRED_DETAIL_PAYLOAD_FIELDS = ("elderly_support",)
DETAIL_FIELD_LABELS = {
    "elderly_support": "노부모 부양 여부",
}


@dataclass(frozen=True)
class DiagnosisForm:
    bankbook_type: str | None
    bankbook_join_date: date | None
    bankbook_payments: int
    bankbook_balance: int
    region: str | None
    residence_period_years: int | None
    is_homeless: bool | None
    homeless_period_years: int | None
    is_household_head: bool | None
    num_household_members: int | None
    birth_year: int
    marital_status: str | None
    marriage_period_years: int | None
    child_status: str | None
    minor_children_status: str | None
    minor_child_count: int | None
    is_dual_income: bool | None = None
    average_monthly_income: int | None = None
    has_property_history: bool | None = None
    total_assets: int | None = None


def calculate_joined_months(joined_at: date | None, today: date | None = None) -> int | None:
    if joined_at is None:
        return None
    today = today or date.today()
    months = (today.year - joined_at.year) * 12 + today.month - joined_at.month
    if today.day < joined_at.day:
        months -= 1
    return max(months, 0)


def validate_form(form: DiagnosisForm) -> list[str]:
    errors: list[str] = []
    if not form.bankbook_type:
        errors.append("통장 종류를 선택해야 합니다.")
    if form.bankbook_join_date is None:
        errors.append("가입일을 입력해야 합니다.")
    if form.bankbook_payments < 0:
        errors.append("납입 횟수는 0 이상이어야 합니다.")
    if form.bankbook_balance < 0:
        errors.append("예치금은 0 이상이어야 합니다.")
    if not form.region:
        errors.append("거주 지역을 선택해야 합니다.")
    if form.residence_period_years is None or form.residence_period_years < 0:
        errors.append("해당 지역 거주기간은 0 이상이어야 합니다.")
    if form.is_homeless is None:
        errors.append("무주택 여부를 선택해야 합니다.")
    if form.is_homeless and form.homeless_period_years is None:
        errors.append("무주택인 경우 무주택 기간을 선택해야 합니다.")
    if form.is_household_head is None:
        errors.append("세대주 여부를 선택해야 합니다.")
    if form.num_household_members is None or form.num_household_members < 1:
        errors.append("세대 구성원 수는 본인을 포함해 1명 이상이어야 합니다.")
    if form.birth_year < 1900:
        errors.append("출생 연도를 확인해야 합니다.")
    if form.marital_status is None:
        errors.append("혼인 상태를 선택해야 합니다.")
    if form.marital_status in {"MARRIED", "ENGAGED"} and form.marriage_period_years is None:
        errors.append("기혼 또는 예비 신혼부부인 경우 혼인기간을 입력해야 합니다.")
    if form.marriage_period_years is not None and form.marriage_period_years < 0:
        errors.append("혼인기간은 0 이상이어야 합니다.")
    if form.child_status is None:
        errors.append("자녀 여부를 선택해야 합니다.")
    if form.child_status == "HAS_CHILD":
        if form.minor_child_count is None:
            errors.append("자녀가 있는 경우 미성년 자녀 수를 입력해야 합니다.")
        elif form.minor_child_count < 1:
            errors.append("자녀가 있음이면 미성년 자녀 수를 1명 이상으로 입력해야 합니다.")
        if form.minor_children_status is None:
            errors.append("만 19세 미만 자녀 수 범주를 확인해야 합니다.")
    if form.minor_child_count is not None and form.minor_child_count < 0:
        errors.append("미성년 자녀 수는 0 이상이어야 합니다.")
    if form.is_dual_income is None:
        errors.append("맞벌이 여부를 선택해야 합니다.")
    if form.average_monthly_income is None:
        errors.append("가구 월평균 소득을 입력해야 합니다.")
    elif form.average_monthly_income < 0:
        errors.append("가구 월평균 소득은 0 이상이어야 합니다.")
    if form.has_property_history is None:
        errors.append("주택 구입/소유 이력을 선택해야 합니다.")
    if form.total_assets is None:
        errors.append("총자산을 입력해야 합니다.")
    elif form.total_assets < 0:
        errors.append("총자산은 0 이상이어야 합니다.")
    return errors


def validate_detail_payload(detail_payload: dict[str, str | None] | None) -> list[str]:
    detail_payload = detail_payload or {}
    errors: list[str] = []
    for field in REQUIRED_DETAIL_PAYLOAD_FIELDS:
        if detail_payload.get(field) is None:
            errors.append(f"{DETAIL_FIELD_LABELS[field]}를 선택해야 합니다. 모르면 '모름'을 선택하세요.")
    return errors


def validate_step(
    step_key: str,
    form: DiagnosisForm,
    detail_payload: dict[str, str | None] | None = None,
) -> list[str]:
    errors = validate_form(form)
    if step_key == "account":
        return [error for error in errors if error.startswith(("통장", "가입일", "납입", "예치금"))]
    if step_key == "housing":
        return [
            error
            for error in errors
            if error.startswith(("거주", "해당 지역", "무주택", "세대주", "세대 구성원"))
        ]
    if step_key == "family":
        return [
            error
            for error in errors
            if error.startswith(("출생", "혼인", "기혼", "자녀", "만 19세", "미성년"))
        ]
    if step_key == "optional":
        optional_errors = [
            error
            for error in errors
            if error.startswith(("가구", "맞벌이", "주택", "총자산"))
        ]
        return optional_errors + validate_detail_payload(detail_payload)
    return errors


def build_profile_payload(form: DiagnosisForm) -> dict[str, Any]:
    minor_children_status = form.minor_children_status
    if form.child_status == "NO_CHILD":
        minor_children_status = "UNDER_TWO"

    return {
        "bankbook_type": form.bankbook_type,
        "bankbook_join_date": form.bankbook_join_date.isoformat()
        if form.bankbook_join_date
        else None,
        "bankbook_joined_months": calculate_joined_months(form.bankbook_join_date),
        "bankbook_payments": form.bankbook_payments,
        "bankbook_balance": form.bankbook_balance,
        "region": form.region,
        "residence_period_years": form.residence_period_years,
        "is_homeless": form.is_homeless,
        "homeless_period_years": form.homeless_period_years if form.is_homeless else None,
        "is_household_head": form.is_household_head,
        "num_household_members": form.num_household_members,
        "birth_year": form.birth_year,
        "marriage_period_years": form.marriage_period_years,
        "minor_children_status": minor_children_status,
        "minor_child_count": form.minor_child_count,
        "has_two_or_more_minor_children": (
            form.minor_child_count >= 2
            if form.minor_child_count is not None
            else minor_children_status == "TWO_OR_MORE"
        ),
        "is_dual_income": form.is_dual_income,
        "average_monthly_income": form.average_monthly_income,
        "has_property_history": form.has_property_history,
        "total_assets": form.total_assets,
    }


def build_backend_compatible_payload(
    form: DiagnosisForm,
    detail_payload: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    profile = build_profile_payload(form)
    detail = build_profile_detail_payload(form, detail_payload)
    is_elderly_parent = detail.get("elderly_support") == "MEETS_65_AND_3Y"

    clean_profile = {
        "bankbook_type": profile["bankbook_type"] or "",
        "bankbook_join_date": profile["bankbook_join_date"] or "",
        "bankbook_payments": profile["bankbook_payments"],
        "bankbook_balance": profile["bankbook_balance"],
        "region": profile["region"] or "",
        "residence_period_years": profile["residence_period_years"] or 0,
        "is_homeless": bool(profile["is_homeless"]),
        "housing_ownership": not bool(profile["is_homeless"]),
        "homeless_period_years": profile["homeless_period_years"] or 0,
        "is_household_head": bool(profile["is_household_head"]),
        "num_household_members": max(int(profile["num_household_members"] or 1), 1),
        "marital_status": form.marital_status,
        "marriage_period_years": profile["marriage_period_years"],
        "child_status": form.child_status,
        "birth_year": profile["birth_year"],
        "minor_children_status": profile["minor_children_status"] or "UNKNOWN",
        "minor_child_count": profile["minor_child_count"],
        "is_elderly_parent": is_elderly_parent,
        "elderly_parent_years": 3 if is_elderly_parent else None,
        "is_dual_income": profile["is_dual_income"],
        "average_monthly_income": profile["average_monthly_income"] or 0,
        "has_property_history": bool(profile["has_property_history"]),
        "total_assets": profile["total_assets"] or 0,
    }
    return {"profile": clean_profile}


def build_profile_detail_payload(
    form: DiagnosisForm,
    detail_payload: dict[str, str | None] | None = None,
) -> dict[str, str | None]:
    """Return detail inputs collected before the diagnosis result screen."""
    normalized = {field: None for field in DETAIL_PAYLOAD_FIELDS}
    if detail_payload:
        for field in DETAIL_PAYLOAD_FIELDS:
            normalized[field] = detail_payload.get(field)

    if form.marital_status not in {"MARRIED", "ENGAGED"}:
        normalized["marriage_period"] = None

    if form.child_status != "HAS_CHILD":
        normalized["youngest_child_age_group"] = None
        normalized["child_count_group"] = None
    elif normalized["child_count_group"] is None:
        if form.minor_children_status == "TWO_OR_MORE":
            normalized["child_count_group"] = "TWO_OR_MORE"
        elif form.minor_children_status == "UNDER_TWO":
            normalized["child_count_group"] = "ONE"

    if normalized["housing_history"] is None:
        if form.has_property_history is True:
            normalized["housing_history"] = "OTHER_HISTORY"
        elif form.has_property_history is False:
            normalized["housing_history"] = "NO_HISTORY"

    return normalized
