from __future__ import annotations

from datetime import date
from typing import Any

from src.engine.tools.calculator.housing_subscription_score import (
    HousingSubscriptionScoreInput,
    HousingSubscriptionScoreOutput,
    _add_years,
    _full_months_between,
    _full_years_between,
    _score_dependent_family,
    _score_homeless_years,
    _score_subscription_months,
    calculate_housing_subscription_score,
)
from src.engine.tools.calculator.housing_subscription_score_constants import (
    get_primary_source_ref,
    load_housing_subscription_score_table,
)
from src.engine.tools.calculator.housing_subscription_score_response_adapter import (
    GENERAL_SCORE_SUPPLY_TYPE,
    RESULT_STATUS_NEEDS_REVIEW,
    _assert_diagnose_response_fragment_shape,
    _assert_supply_diagnosis_shape,
    _dedupe,
    build_general_score_supply_diagnosis,
)


PARTIAL_SCORE_NOTICE = (
    "현재 입력값만으로 계산 가능한 항목 기준의 참고 점수입니다. "
    "누락된 항목은 점수에 포함하지 않았으며, 실제 청약 가점 총점과 다를 수 있습니다."
)


def build_partial_general_score_supply_diagnosis(
    input_data: dict[str, Any],
) -> dict[str, Any]:
    """Build a SupplyDiagnosis-shaped partial score result."""
    exact_score = _try_calculate_complete_score(input_data)
    if exact_score is not None:
        return build_general_score_supply_diagnosis(exact_score)

    table = load_housing_subscription_score_table()
    context = _PartialScoreContext(table=table)

    _append_partial_homeless_score(input_data, context)
    _append_partial_dependent_family_score(input_data, context)
    _append_partial_subscription_score(input_data, context)
    _append_partial_spouse_subscription_score(input_data, context)

    reasons = [PARTIAL_SCORE_NOTICE]
    reasons.append(f"계산 가능 항목 점수: {context.calculable_score}점")
    reasons.extend(context.reasons)
    if not context.reasons:
        reasons.append("현재 입력값만으로는 계산 가능한 가점 항목이 없습니다.")

    payload = {
        "supply_type": GENERAL_SCORE_SUPPLY_TYPE,
        "status": RESULT_STATUS_NEEDS_REVIEW,
        "reasons": reasons,
        "missing_checks": _dedupe(context.missing_inputs),
        "next_questions": _dedupe(context.next_questions),
        "source_refs": [get_primary_source_ref()],
    }
    _assert_supply_diagnosis_shape(payload)
    return payload


def build_partial_general_score_diagnose_response_fragment(
    input_data: dict[str, Any],
) -> dict[str, Any]:
    """Return a DiagnoseResponse-compatible fragment for partial score mode."""
    supply_diagnosis = build_partial_general_score_supply_diagnosis(input_data)
    warnings = [PARTIAL_SCORE_NOTICE]
    warnings.extend(supply_diagnosis["missing_checks"])

    fragment = {
        "result_status": supply_diagnosis["status"],
        "candidate_supply_types": [supply_diagnosis],
        "missing_inputs": list(supply_diagnosis["missing_checks"]),
        "next_questions": list(supply_diagnosis["next_questions"]),
        "warnings": _dedupe(warnings),
    }
    _assert_diagnose_response_fragment_shape(fragment)
    return fragment


class _PartialScoreContext:
    def __init__(self, table: dict[str, Any]) -> None:
        self.table = table
        self.calculable_score = 0
        self.subscription_score: int | None = None
        self.reasons: list[str] = []
        self.missing_inputs: list[str] = []
        self.next_questions: list[str] = []

    def add_score(self, reason: str, score: int) -> None:
        self.calculable_score += score
        self.reasons.append(reason)

    def add_missing(self, label: str, question_key: str) -> None:
        self.missing_inputs.append(label)
        self.next_questions.append(question_key)


def _try_calculate_complete_score(
    input_data: dict[str, Any],
) -> HousingSubscriptionScoreOutput | None:
    payload = _build_complete_score_input(input_data)
    if payload is None:
        return None
    return calculate_housing_subscription_score(payload)


def _build_complete_score_input(
    input_data: dict[str, Any],
) -> HousingSubscriptionScoreInput | None:
    is_married = _get_bool(input_data, "is_married")
    include_spouse = _get_bool(input_data, "include_spouse_subscription_score") or False
    payload = {
        "birth_date": _get_date(input_data, "birth_date"),
        "is_married": is_married,
        "marriage_date": _get_date(input_data, "marriage_date"),
        "homeless_start_date": _get_date(input_data, "homeless_start_date"),
        "dependent_family_count": _get_int(input_data, "dependent_family_count"),
        "subscription_join_date": _get_date(
            input_data,
            "subscription_join_date",
            "bankbook_join_date",
        ),
        "announcement_date": _get_date(input_data, "announcement_date"),
        "spouse_subscription_join_date": _get_date(
            input_data,
            "spouse_subscription_join_date",
        ),
        "include_spouse_subscription_score": include_spouse,
    }

    required_keys = {
        "birth_date",
        "is_married",
        "dependent_family_count",
        "subscription_join_date",
        "announcement_date",
    }
    if any(payload[key] is None for key in required_keys):
        return None
    if payload["is_married"] is True and payload["marriage_date"] is None:
        return None
    if include_spouse and payload["spouse_subscription_join_date"] is None:
        return None

    try:
        return HousingSubscriptionScoreInput.model_validate(payload)
    except ValueError:
        return None


def _append_partial_homeless_score(
    input_data: dict[str, Any],
    context: _PartialScoreContext,
) -> None:
    is_homeless = _get_bool(input_data, "is_homeless")
    if is_homeless is False:
        context.add_score("무주택기간: 무주택자가 아닌 것으로 입력되어 0점 / 32점", 0)
        return

    homeless_period_years = _get_int(input_data, "homeless_period_years")
    if homeless_period_years is not None:
        score = _score_homeless_years(homeless_period_years, context.table)
        context.add_score(
            f"무주택기간: 사용자 입력 {homeless_period_years}년 기준 {score}점 / 32점",
            score,
        )
        return

    birth_date = _get_date(input_data, "birth_date")
    announcement_date = _get_date(input_data, "announcement_date")
    is_married = _get_bool(input_data, "is_married")
    marriage_date = _get_date(input_data, "marriage_date")
    homeless_start_date = _get_date(input_data, "homeless_start_date")

    if birth_date is None:
        context.add_missing("생년월일", "birth_date")
    if announcement_date is None:
        context.add_missing("입주자모집공고일", "announcement_date")
    if is_married is None:
        context.add_missing("혼인 여부", "is_married")
    if is_married is True and marriage_date is None:
        context.add_missing("혼인신고일", "marriage_date")
    if _get_bool(input_data, "has_property_history") is True and homeless_start_date is None:
        context.add_missing("과거 주택 소유 및 처분 이력 기준일", "homeless_start_date")

    if (
        birth_date is None
        or announcement_date is None
        or is_married is None
        or (is_married is True and marriage_date is None)
        or (_get_bool(input_data, "has_property_history") is True and homeless_start_date is None)
    ):
        return

    age_30_date = _add_years(birth_date, 30)
    if not is_married and announcement_date < age_30_date:
        context.add_score("무주택기간: 만 30세 미만 미혼 기준 0점 / 32점", 0)
        return

    basis_date = age_30_date
    if is_married and marriage_date and marriage_date < age_30_date:
        basis_date = marriage_date
    if homeless_start_date and homeless_start_date > basis_date:
        basis_date = homeless_start_date

    years = _full_years_between(basis_date, announcement_date)
    score = _score_homeless_years(years, context.table)
    context.add_score(f"무주택기간: {years}년, {score}점 / 32점", score)


def _append_partial_dependent_family_score(
    input_data: dict[str, Any],
    context: _PartialScoreContext,
) -> None:
    dependent_family_count = _get_int(input_data, "dependent_family_count")
    if dependent_family_count is None:
        if _get_int(input_data, "num_household_members") is not None:
            context.reasons.append(
                "세대원 수는 부양가족 수와 다르므로 부양가족 점수로 자동 변환하지 않았습니다."
            )
        context.add_missing("부양가족 수", "dependent_family_count")
        return

    score = _score_dependent_family(dependent_family_count, context.table)
    context.add_score(
        f"부양가족: {dependent_family_count}명 기준 {score}점 / 35점",
        score,
    )


def _append_partial_subscription_score(
    input_data: dict[str, Any],
    context: _PartialScoreContext,
) -> None:
    subscription_join_date = _get_date(
        input_data,
        "subscription_join_date",
        "bankbook_join_date",
    )
    announcement_date = _get_date(input_data, "announcement_date")
    joined_months = _get_int(
        input_data,
        "subscription_joined_months",
        "bankbook_joined_months",
        "joined_months",
    )

    if subscription_join_date is not None and announcement_date is not None:
        months = _full_months_between(subscription_join_date, announcement_date)
        score = _score_subscription_months(months, context.table)
        context.subscription_score = score
        context.add_score(
            f"청약통장 가입기간: {months // 12}년, {score}점 / 17점",
            score,
        )
        return

    if joined_months is not None:
        score = _score_subscription_months(joined_months, context.table)
        context.subscription_score = score
        context.add_score(
            f"청약통장 가입기간: 입력된 {joined_months}개월 기준 {score}점 / 17점",
            score,
        )
        if announcement_date is None:
            context.add_missing("입주자모집공고일", "announcement_date")
        return

    context.add_missing("청약통장 가입일", "subscription_join_date")
    if announcement_date is None:
        context.add_missing("입주자모집공고일", "announcement_date")


def _append_partial_spouse_subscription_score(
    input_data: dict[str, Any],
    context: _PartialScoreContext,
) -> None:
    include_spouse = _get_bool(input_data, "include_spouse_subscription_score")
    if include_spouse is not True:
        return

    spouse_join_date = _get_date(input_data, "spouse_subscription_join_date")
    announcement_date = _get_date(input_data, "announcement_date")
    if spouse_join_date is None:
        context.add_missing("배우자 청약통장 가입일", "spouse_subscription_join_date")
    if announcement_date is None:
        context.add_missing("입주자모집공고일", "announcement_date")
    if spouse_join_date is None or announcement_date is None:
        return
    if context.subscription_score is None:
        context.add_missing("청약통장 가입기간", "subscription_join_date")
        return

    spouse_months = _full_months_between(spouse_join_date, announcement_date)
    spouse_counted_months = spouse_months // 2
    raw_score = _score_subscription_months(spouse_counted_months, context.table)
    score = min(raw_score, context.table["score_limits"]["spouse_subscription_bonus"])
    subscription_cap = context.table["score_limits"]["subscription_period"]
    merged_score = min(context.subscription_score + score, subscription_cap)
    effective_bonus = merged_score - context.subscription_score
    context.add_score(f"배우자 청약통장 가입기간 합산: {effective_bonus}점", effective_bonus)


def _get_raw(input_data: dict[str, Any], *keys: str) -> Any:
    nested_candidates = [
        input_data,
        input_data.get("profile") if isinstance(input_data.get("profile"), dict) else {},
        (
            input_data.get("subscription_account_detail")
            if isinstance(input_data.get("subscription_account_detail"), dict)
            else {}
        ),
    ]
    for key in keys:
        for candidate in nested_candidates:
            if key in candidate and candidate[key] is not None:
                return candidate[key]
    return None


def _get_date(input_data: dict[str, Any], *keys: str) -> date | None:
    value = _get_raw(input_data, *keys)
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _get_int(input_data: dict[str, Any], *keys: str) -> int | None:
    value = _get_raw(input_data, *keys)
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def _get_bool(input_data: dict[str, Any], key: str) -> bool | None:
    value = _get_raw(input_data, key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized in {"TRUE", "YES", "Y", "1", "MARRIED", "기혼"}:
            return True
        if normalized in {
            "FALSE",
            "NO",
            "N",
            "0",
            "NOT_MARRIED",
            "ENGAGED",
            "미혼",
            "예비",
        }:
            return False

    if key == "is_married":
        marital_status = _get_raw(input_data, "marital_status")
        if isinstance(marital_status, str):
            normalized = marital_status.strip().upper()
            if normalized in {"MARRIED", "기혼"}:
                return True
            if normalized in {"NOT_MARRIED", "ENGAGED", "미혼", "예비"}:
                return False

    return None
