"""Step-by-step input UI for the diagnosis wizard."""

from __future__ import annotations

from datetime import date

import streamlit as st

from components.ui import card_choice, render_explanation
from domain.constants import (
    ACCOUNT_TYPE_OPTIONS,
    CHILD_STATUS_OPTIONS,
    DETAIL_FIELD_OPTIONS,
    HOMELESS_PERIOD_OPTIONS,
    MARITAL_STATUS_OPTIONS,
    MINOR_CHILDREN_OPTIONS,
    PROPERTY_HISTORY_OPTIONS,
    REGION_OPTIONS,
    YES_NO_OPTIONS,
)
from services.payload import validate_step
from state.diagnosis_state import (
    STEPS,
    build_detail_payload,
    build_form_from_state,
    detail_widget_key,
    persist_widget,
    widget_key,
)
from views.diagnosis_result import run_diagnosis


def render_stepper(active_index: int) -> None:
    labels = []
    for index, (_, label) in enumerate(STEPS):
        prefix = "●" if index == active_index else "○"
        labels.append(f"{prefix} {index + 1}. {label}")
    st.caption("   ".join(labels))


def render_detail_card_choice(field: str, *, columns: int = 3) -> object:
    config = DETAIL_FIELD_OPTIONS[field]
    return card_choice(
        config["label"],
        detail_widget_key(field),
        config["options"],
        columns=columns,
    )


def clear_detail_values(*fields: str) -> None:
    for field in fields:
        st.session_state.pop(detail_widget_key(field), None)


def render_account_step() -> None:
    st.subheader("1. 통장 정보")
    render_explanation(
        "왜 필요한가요?",
        [
            "통장 종류는 신청 가능한 주택 유형과 기준을 나누는 첫 조건입니다.",
            "가입일은 가입 기간을 계산해 1순위 요건을 확인하는 데 사용합니다.",
            "납입 횟수와 예치금은 지역별/공급유형별 기본 충족 여부를 판단하는 핵심 값입니다.",
        ],
    )
    st.selectbox(
        "통장 종류",
        ACCOUNT_TYPE_OPTIONS,
        index=None,
        placeholder="통장 종류를 선택하세요",
        key=widget_key("bankbook_type"),
        on_change=persist_widget,
        args=("bankbook_type",),
    )
    col_1, col_2, col_3 = st.columns(3)
    with col_1:
        st.date_input(
            "가입일",
            min_value=date(1980, 1, 1),
            max_value=date.today(),
            key=widget_key("bankbook_join_date", date(2024, 1, 1)),
            on_change=persist_widget,
            args=("bankbook_join_date",),
        )
    with col_2:
        st.number_input(
            "납입 횟수",
            min_value=0,
            step=1,
            key=widget_key("bankbook_payments", 0),
            on_change=persist_widget,
            args=("bankbook_payments",),
        )
    with col_3:
        st.number_input(
            "예치금",
            min_value=0,
            step=10000,
            key=widget_key("bankbook_balance", 0),
            on_change=persist_widget,
            args=("bankbook_balance",),
        )


def render_housing_step() -> None:
    st.subheader("2. 무주택 및 세대 조건")
    render_explanation(
        "왜 필요한가요?",
        [
            "거주지역은 지역별 예치금 기준과 해당 지역 모집공고 조건을 비교할 때 필요합니다.",
            "무주택 여부와 기간은 특별공급과 일반공급 가점 판단에서 중요한 기준입니다.",
            "세대주 여부와 세대원 수는 공고별 신청 자격과 세대 기준 확인에 사용합니다.",
        ],
    )
    st.selectbox(
        "거주지역",
        REGION_OPTIONS,
        index=None,
        placeholder="거주지역을 선택하세요",
        key=widget_key("region"),
        on_change=persist_widget,
        args=("region",),
    )
    is_homeless = card_choice("무주택 여부", "is_homeless", YES_NO_OPTIONS, columns=2)
    if is_homeless is True:
        card_choice("무주택 기간", "homeless_period_years", HOMELESS_PERIOD_OPTIONS, columns=4)

    is_household_head = card_choice("세대주 여부", "is_household_head", YES_NO_OPTIONS, columns=2)
    if is_household_head is True:
        st.number_input(
            "세대원 수",
            min_value=1,
            step=1,
            key=widget_key("num_household_members", 1),
            on_change=persist_widget,
            args=("num_household_members",),
        )


def render_family_step() -> None:
    st.subheader("3. 혼인/출생/자녀 조건")
    render_explanation(
        "왜 필요한가요?",
        [
            "혼인 상태는 신혼부부 특별공급 후보 판단에 직접 사용합니다.",
            "출생 연도는 청년, 생애최초, 노부모부양 등 연령 조건과 연결될 수 있습니다.",
            "자녀 여부와 만 19세 미만 자녀 수는 다자녀·신생아 특별공급 후보 판단에 사용합니다.",
        ],
    )
    marital_status = card_choice(
        "혼인 상태",
        "marital_status",
        MARITAL_STATUS_OPTIONS,
        columns=3,
    )
    if marital_status in {"MARRIED", "ENGAGED"}:
        st.caption("혼인기간은 신혼부부 특별공급 후보를 좁히는 데 사용합니다. 모르면 '모름'을 선택할 수 있습니다.")
        render_detail_card_choice("marriage_period", columns=3)
    else:
        clear_detail_values("marriage_period")

    st.number_input(
        "출생 연도",
        min_value=1900,
        max_value=2100,
        step=1,
        key=widget_key("birth_year", 1990),
        on_change=persist_widget,
        args=("birth_year",),
    )
    child_status = card_choice("자녀 여부", "child_status", CHILD_STATUS_OPTIONS, columns=2)
    if child_status == "HAS_CHILD":
        card_choice(
            "만 19세 미만 자녀 수",
            "minor_children_status",
            MINOR_CHILDREN_OPTIONS,
            columns=2,
        )
        st.caption("가장 어린 자녀 연령은 신생아 특별공급 후보가 있을 때만 상세 판단에 사용합니다.")
        render_detail_card_choice("youngest_child_age_group", columns=4)
    elif child_status == "NO_CHILD":
        clear_detail_values("youngest_child_age_group", "child_count_group")
        st.caption("자녀가 없으면 미성년 자녀 수는 자동으로 2명 미만으로 전달됩니다.")


def render_optional_step() -> None:
    st.subheader("4. 선택 정보")
    render_explanation(
        "왜 선택 정보인가요?",
        [
            "가구 평균소득과 자산은 특별공급 세부 기준을 더 정밀하게 비교할 때 필요합니다.",
            "주택 구입 이력은 생애최초 등 일부 제도 판단에 영향을 줄 수 있습니다.",
            "지금 모르면 비워두고 진행해도 됩니다. 결과에서는 추가 확인 항목으로 남깁니다.",
        ],
    )

    include_income = st.checkbox(
        "가구 평균소득 입력하기",
        key=widget_key("include_average_monthly_income", False),
        on_change=persist_widget,
        args=("include_average_monthly_income",),
    )
    if include_income:
        st.number_input(
            "가구 평균소득",
            min_value=0,
            step=100000,
            key=widget_key("average_monthly_income", 0),
            on_change=persist_widget,
            args=("average_monthly_income",),
        )

    include_property_history = st.checkbox(
        "주택 구입 이력 입력하기",
        key=widget_key("include_property_history", False),
        on_change=persist_widget,
        args=("include_property_history",),
    )
    if include_property_history:
        card_choice(
            "주택 구입 이력",
            "has_property_history",
            PROPERTY_HISTORY_OPTIONS,
            columns=2,
        )

    include_assets = st.checkbox(
        "자산 입력하기",
        key=widget_key("include_total_assets", False),
        on_change=persist_widget,
        args=("include_total_assets",),
    )
    if include_assets:
        st.number_input(
            "자산",
            min_value=0,
            step=1000000,
            key=widget_key("total_assets", 0),
            on_change=persist_widget,
            args=("total_assets",),
        )

    st.caption("노부모 부양 여부는 필수 선택입니다. 정확히 모르면 '모름'을 선택하세요.")
    render_detail_card_choice("elderly_support", columns=3)


def render_navigation(step_index: int) -> None:
    st.divider()
    col_prev, col_next = st.columns([1, 1])
    with col_prev:
        if st.button("이전", disabled=step_index == 0, use_container_width=True):
            st.session_state["diagnosis_step"] = max(step_index - 1, 0)
            st.rerun()

    with col_next:
        if step_index >= len(STEPS) - 1:
            return
        step_key, _ = STEPS[step_index]
        form = build_form_from_state()
        errors = validate_step(step_key, form, build_detail_payload())
        if errors:
            for error in errors:
                st.caption(error)
        if st.button("다음", disabled=bool(errors), type="primary", use_container_width=True):
            if step_key == "optional":
                run_diagnosis(form)
            st.session_state["diagnosis_step"] = min(step_index + 1, len(STEPS) - 1)
            st.rerun()
