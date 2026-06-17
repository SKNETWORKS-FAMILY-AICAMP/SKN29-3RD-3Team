"""Streamlit session-state helpers for the diagnosis flow."""

from __future__ import annotations

import streamlit as st

from domain.constants import DETAIL_FIELD_OPTIONS
from services.payload import DiagnosisForm


STEPS = [
    ("account", "통장"),
    ("housing", "주택/세대"),
    ("family", "혼인/자녀"),
    ("optional", "소득/자산"),
    ("announcement", "공고 정보"),
    ("result", "결과"),
]

DIAGNOSIS_STATE_KEYS = [
    "bankbook_type",
    "bankbook_join_date",
    "bankbook_payments",
    "bankbook_balance",
    "region",
    "residence_period_years",
    "is_homeless",
    "homeless_period_years",
    "is_household_head",
    "num_household_members",
    "birth_year",
    "marital_status",
    "marriage_period_years",
    "child_status",
    "minor_children_status",
    "minor_child_count",
    "dual_income_status",
    "average_monthly_income",
    "has_property_history",
    "total_assets",
    "wants_detailed_diagnosis_choice",
    "announcement_text",
]

DIAGNOSIS_RESPONSE_KEYS = [
    "last_diagnosis_response",
    "last_detail_response",
    "last_simulate_response",
    "last_diagnosis_session_id",
    "last_profile_payload",
    "last_backend_payload",
    "last_detail_payload",
    "last_api_error",
]


def build_form_from_state() -> DiagnosisForm:
    child_status = st.session_state.get("child_status")
    minor_child_count = (
        0
        if child_status == "NO_CHILD"
        else int(st.session_state.get("minor_child_count", 1))
        if child_status == "HAS_CHILD"
        else None
    )
    minor_children_status = (
        "UNDER_TWO"
        if child_status == "NO_CHILD"
        else "TWO_OR_MORE"
        if minor_child_count is not None and minor_child_count >= 2
        else "UNDER_TWO"
        if minor_child_count is not None
        else st.session_state.get("minor_children_status")
    )
    dual_income_map = {"맞벌이": True, "외벌이": False}

    return DiagnosisForm(
        bankbook_type=st.session_state.get("bankbook_type"),
        bankbook_join_date=st.session_state.get("bankbook_join_date"),
        bankbook_payments=int(st.session_state.get("bankbook_payments", 0)),
        bankbook_balance=int(st.session_state.get("bankbook_balance", 0)),
        region=st.session_state.get("region"),
        residence_period_years=int(st.session_state.get("residence_period_years", 0)),
        is_homeless=st.session_state.get("is_homeless"),
        homeless_period_years=st.session_state.get("homeless_period_years")
        if st.session_state.get("is_homeless") is True
        else None,
        is_household_head=st.session_state.get("is_household_head"),
        num_household_members=max(int(st.session_state.get("num_household_members", 1)), 1),
        birth_year=int(st.session_state.get("birth_year", 1990)),
        marital_status=st.session_state.get("marital_status"),
        marriage_period_years=(
            int(st.session_state.get("marriage_period_years", 0))
            if st.session_state.get("marital_status") in {"MARRIED", "ENGAGED"}
            else None
        ),
        child_status=child_status,
        minor_children_status=minor_children_status,
        minor_child_count=minor_child_count,
        is_dual_income=dual_income_map.get(st.session_state.get("dual_income_status")),
        average_monthly_income=int(st.session_state.get("average_monthly_income", 0)),
        has_property_history=st.session_state.get("has_property_history"),
        total_assets=int(st.session_state.get("total_assets", 0)),
    )


def widget_key(state_key: str, default: object | None = None) -> str:
    widget_key_value = f"_input_{state_key}"
    if state_key not in st.session_state and default is not None:
        st.session_state[state_key] = default
    if widget_key_value not in st.session_state:
        st.session_state[widget_key_value] = st.session_state.get(state_key, default)
    return widget_key_value


def persist_widget(state_key: str) -> None:
    st.session_state[state_key] = st.session_state.get(widget_key(state_key))
    st.session_state.pop("last_diagnosis_response", None)
    st.session_state.pop("last_detail_response", None)


def detail_widget_key(field: str) -> str:
    return f"_detail_{field}"


def build_detail_payload() -> dict[str, str | None]:
    return {
        field: st.session_state.get(detail_widget_key(field))
        for field in DETAIL_FIELD_OPTIONS
    }


def build_announcement_payload() -> str | None:
    announcement_text = str(st.session_state.get("announcement_text") or "").strip()
    return announcement_text or None


def collect_response_questions(response: dict) -> list[str]:
    questions: list[str] = []
    questions.extend(response.get("next_questions", []))
    for item in response.get("candidate_supply_types", []):
        questions.extend(item.get("next_questions", []))

    result: list[str] = []
    seen: set[str] = set()
    for question in questions:
        if question not in seen:
            seen.add(question)
            result.append(question)
    return result


def reset_diagnosis_state() -> None:
    """테마/챗봇은 유지하고 자가진단 입력과 결과 상태만 초기화한다."""
    for key in DIAGNOSIS_STATE_KEYS:
        st.session_state.pop(key, None)
        st.session_state.pop(f"_input_{key}", None)

    for field in DETAIL_FIELD_OPTIONS:
        st.session_state.pop(detail_widget_key(field), None)

    for key in DIAGNOSIS_RESPONSE_KEYS:
        st.session_state.pop(key, None)

    for key in list(st.session_state.keys()):
        if str(key).startswith("validation_errors_"):
            st.session_state.pop(key, None)

    st.session_state["diagnosis_step"] = 0
