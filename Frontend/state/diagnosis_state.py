"""Streamlit session-state helpers for the diagnosis flow."""

from __future__ import annotations

import streamlit as st

from domain.constants import DETAIL_FIELD_OPTIONS
from services.payload import DiagnosisForm


STEPS = [
    ("account", "통장"),
    ("housing", "주택/세대"),
    ("family", "혼인/자녀"),
    ("optional", "선택 정보"),
    ("result", "결과"),
]


def build_form_from_state() -> DiagnosisForm:
    include_income = bool(st.session_state.get("include_average_monthly_income"))
    include_property_history = bool(st.session_state.get("include_property_history"))
    include_assets = bool(st.session_state.get("include_total_assets"))
    child_status = st.session_state.get("child_status")
    minor_children_status = (
        "UNDER_TWO"
        if child_status == "NO_CHILD"
        else st.session_state.get("minor_children_status")
    )

    return DiagnosisForm(
        bankbook_type=st.session_state.get("bankbook_type"),
        bankbook_join_date=st.session_state.get("bankbook_join_date"),
        bankbook_payments=int(st.session_state.get("bankbook_payments") or 0),
        bankbook_balance=int(st.session_state.get("bankbook_balance") or 0),
        region=st.session_state.get("region"),
        is_homeless=st.session_state.get("is_homeless"),
        homeless_period_years=st.session_state.get("homeless_period_years")
        if st.session_state.get("is_homeless") is True
        else None,
        is_household_head=st.session_state.get("is_household_head"),
        num_household_members=st.session_state.get("num_household_members")
        if st.session_state.get("is_household_head") is True
        else None,
        birth_year=int(st.session_state.get("birth_year") or 1990),
        marital_status=st.session_state.get("marital_status"),
        child_status=child_status,
        minor_children_status=minor_children_status,
        average_monthly_income=int(st.session_state.get("average_monthly_income") or 0)
        if include_income
        else None,
        has_property_history=st.session_state.get("has_property_history")
        if include_property_history
        else None,
        total_assets=int(st.session_state.get("total_assets") or 0) if include_assets else None,
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
