from __future__ import annotations

from typing import Any

from src.engine.tools.calculator.housing_subscription_score import (
    HousingSubscriptionScoreOutput,
)


RESULT_STATUS_POSSIBLE = "가능성 있음"
RESULT_STATUS_NEEDS_REVIEW = "추가 확인 필요"
GENERAL_SCORE_SUPPLY_TYPE = "일반공급 가점제"

SUPPLY_DIAGNOSIS_KEYS = {
    "supply_type",
    "status",
    "reasons",
    "missing_checks",
    "next_questions",
    "source_refs",
}

DIAGNOSE_RESPONSE_FRAGMENT_KEYS = {
    "result_status",
    "candidate_supply_types",
    "missing_inputs",
    "next_questions",
    "warnings",
}


def build_general_score_supply_diagnosis(
    score: HousingSubscriptionScoreOutput | dict[str, Any],
) -> dict[str, Any]:
    """Map exact MCP score output to the existing SupplyDiagnosis shape."""
    score = _coerce_score_output(score)
    next_questions = _next_questions_from_warnings(score.warnings)

    payload = {
        "supply_type": GENERAL_SCORE_SUPPLY_TYPE,
        "status": _status_from_score(score),
        "reasons": _build_reasons(score),
        "missing_checks": score.warnings if score.need_review else [],
        "next_questions": next_questions,
        "source_refs": score.source_refs,
    }
    _assert_supply_diagnosis_shape(payload)
    return payload


def build_general_score_diagnose_response_fragment(
    score: HousingSubscriptionScoreOutput | dict[str, Any],
) -> dict[str, Any]:
    """Return only fields that already exist on DiagnoseResponse."""
    score = _coerce_score_output(score)
    supply_diagnosis = build_general_score_supply_diagnosis(score)
    next_questions = list(supply_diagnosis["next_questions"])

    fragment = {
        "result_status": supply_diagnosis["status"],
        "candidate_supply_types": [supply_diagnosis],
        "missing_inputs": _missing_inputs_from_next_questions(next_questions),
        "next_questions": next_questions,
        "warnings": list(score.warnings),
    }
    _assert_diagnose_response_fragment_shape(fragment)
    return fragment


def _coerce_score_output(
    score: HousingSubscriptionScoreOutput | dict[str, Any],
) -> HousingSubscriptionScoreOutput:
    if isinstance(score, HousingSubscriptionScoreOutput):
        return score
    return HousingSubscriptionScoreOutput.model_validate(score)


def _status_from_score(score: HousingSubscriptionScoreOutput) -> str:
    if score.need_review:
        return RESULT_STATUS_NEEDS_REVIEW
    return RESULT_STATUS_POSSIBLE


def _build_reasons(score: HousingSubscriptionScoreOutput) -> list[str]:
    reasons = [
        f"일반공급 가점제 총점: {score.total_score}점 / 84점",
        f"무주택기간: {score.homeless_period_years}년, {score.homeless_score}점 / 32점",
        f"부양가족: {score.dependent_family_score}점 / 35점",
        (
            "청약통장 가입기간: "
            f"{score.subscription_period_years}년, {score.subscription_score}점 / 17점"
        ),
    ]

    if score.spouse_subscription_score:
        reasons.append(f"배우자 청약통장 가입기간 합산: {score.spouse_subscription_score}점")

    for assumption in score.assumptions:
        reasons.append(f"계산 가정: {assumption}")

    return reasons


def _next_questions_from_warnings(warnings: list[str]) -> list[str]:
    next_questions: list[str] = []
    for warning in warnings:
        lower_warning = warning.lower()
        if "marriage_date" in lower_warning:
            next_questions.append("marriage_date")
        if "homeless_start_date" in lower_warning or "disposal" in lower_warning:
            next_questions.append("housing_history")
        if "spouse_subscription_join_date" in lower_warning:
            next_questions.append("spouse_subscription_join_date")
    return _dedupe(next_questions)


def _missing_inputs_from_next_questions(next_questions: list[str]) -> list[str]:
    labels = {
        "marriage_date": "혼인신고일",
        "housing_history": "과거 주택 소유 및 처분 이력",
        "spouse_subscription_join_date": "배우자 청약통장 가입일",
    }
    return [labels.get(question, question) for question in next_questions]


def _assert_supply_diagnosis_shape(payload: dict[str, Any]) -> None:
    extra = set(payload) - SUPPLY_DIAGNOSIS_KEYS
    missing = SUPPLY_DIAGNOSIS_KEYS - set(payload)
    if extra or missing:
        raise ValueError(
            f"SupplyDiagnosis-compatible payload mismatch: extra={sorted(extra)}, missing={sorted(missing)}"
        )


def _assert_diagnose_response_fragment_shape(payload: dict[str, Any]) -> None:
    extra = set(payload) - DIAGNOSE_RESPONSE_FRAGMENT_KEYS
    missing = DIAGNOSE_RESPONSE_FRAGMENT_KEYS - set(payload)
    if extra or missing:
        raise ValueError(
            "DiagnoseResponse-compatible fragment mismatch: "
            f"extra={sorted(extra)}, missing={sorted(missing)}"
        )


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
