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
    labels: list[str] = []
    for index, (_, label) in enumerate(STEPS):
        class_name = "cy-step cy-step-active" if index == active_index else "cy-step"
        labels.append(f'<span class="{class_name}">{index + 1}. {label}</span>')
        if index < len(STEPS) - 1:
            labels.append('<span class="cy-step-arrow">→</span>')
    st.markdown(
        '<div class="cy-stepper">' + "".join(labels) + "</div>",
        unsafe_allow_html=True,
    )


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
            "통장 종류와 가입일은 신청 가능한 주택 유형과 기본 자격을 나누는 첫 조건입니다.",
            "가입일은 가입 기간과 1순위 요건 확인에 사용합니다.",
            "납입 횟수와 예치금은 지역과 공급 유형별 충족 여부를 판단하는 핵심 값입니다.",
        ],
        learn_more_question="청약통장은 왜 필요하고 가입일, 납입 횟수, 예치금은 어떻게 판단에 쓰이나요?",
        learn_more_key="learn_more_account",
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
    st.subheader("2. 주택/세대 조건")
    render_explanation(
        "왜 필요한가요?",
        [
            "거주 지역은 예치금 기준과 해당 지역 공고 조건 비교에 필요합니다.",
            "무주택 여부와 기간은 특별공급 및 일반공급 가점 판단에 중요합니다.",
            "세대 구성원 수는 소득 기준과 부양가족 관련 계산에 사용합니다.",
        ],
        learn_more_question="무주택 기준, 무주택 기간, 세대 정보는 청약 자격에 어떻게 반영되나요?",
        learn_more_key="learn_more_housing",
    )
    st.selectbox(
        "거주 지역",
        REGION_OPTIONS,
        index=None,
        placeholder="거주 지역을 선택하세요",
        key=widget_key("region"),
        on_change=persist_widget,
        args=("region",),
    )
    st.number_input(
        "해당 지역 거주기간(년)",
        min_value=0,
        step=1,
        key=widget_key("residence_period_years", 0),
        on_change=persist_widget,
        args=("residence_period_years",),
    )
    is_homeless = card_choice("무주택 여부", "is_homeless", YES_NO_OPTIONS, columns=2)
    if is_homeless is True:
        card_choice("무주택 기간", "homeless_period_years", HOMELESS_PERIOD_OPTIONS, columns=4)
    else:
        st.caption("무주택이 아니면 무주택 기간은 0년으로 전달됩니다.")

    card_choice("세대주 여부", "is_household_head", YES_NO_OPTIONS, columns=2)
    st.number_input(
        "세대 구성원 수",
        min_value=1,
        step=1,
        key=widget_key("num_household_members", 1),
        on_change=persist_widget,
        args=("num_household_members",),
    )
    st.caption("본인을 포함한 인원입니다. 세대주가 아니어도 최소 1명으로 입력해야 합니다.")


def render_family_step() -> None:
    st.subheader("3. 혼인/자녀 조건")
    render_explanation(
        "왜 필요한가요?",
        [
            "혼인 상태와 혼인기간은 신혼부부 특별공급 후보 판단에 사용합니다.",
            "출생 연도는 청년, 생애최초, 노부모 관련 조건과 연결됩니다.",
            "미성년 자녀 수와 가장 어린 자녀 연령은 다자녀/신생아 특별공급 판단에 사용합니다.",
        ],
        learn_more_question="혼인 상태, 출생 연도, 자녀 정보는 특별공급 가능성 판단에 어떻게 쓰이나요?",
        learn_more_key="learn_more_family",
    )
    marital_status = card_choice(
        "혼인 상태",
        "marital_status",
        MARITAL_STATUS_OPTIONS,
        columns=3,
    )
    if marital_status in {"MARRIED", "ENGAGED"}:
        st.number_input(
            "혼인기간(년)",
            min_value=0,
            step=1,
            key=widget_key("marriage_period_years", 0),
            on_change=persist_widget,
            args=("marriage_period_years",),
        )
    else:
        clear_detail_values("marriage_period")
        st.caption("미혼이면 혼인기간은 입력하지 않고 전달하지 않습니다.")

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
        st.number_input(
            "미성년 자녀 수",
            min_value=0,
            step=1,
            key=widget_key("minor_child_count", 1),
            on_change=persist_widget,
            args=("minor_child_count",),
        )
        st.caption("2명 이상이면 다자녀 특별공급 후보 판단에 직접 반영됩니다.")
        render_detail_card_choice("youngest_child_age_group", columns=4)
    elif child_status == "NO_CHILD":
        clear_detail_values("youngest_child_age_group", "child_count_group")
        st.caption("자녀가 없으면 미성년 자녀 수는 0명으로 전달됩니다.")


def render_optional_step() -> None:
    st.subheader("4. 소득/자산/이력 정보")
    render_explanation(
        "왜 필요한가요?",
        [
            "소득과 맞벌이 여부는 신혼부부/생애최초 특별공급의 소득 기준 판단에 사용합니다.",
            "총자산은 자산 기준과 공고 기반 자금 리스크를 계산하는 데 필요합니다.",
            "주택 구입/소유 이력은 생애최초 특별공급 후보 판단에 직접 반영됩니다.",
        ],
        learn_more_question="소득, 자산, 주택 구입 이력은 특별공급과 생애최초 판단에 어떻게 영향을 주나요?",
        learn_more_key="learn_more_optional",
    )
    st.number_input(
        "월평균 소득",
        min_value=0,
        step=100000,
        key=widget_key("average_monthly_income", 0),
        on_change=persist_widget,
        args=("average_monthly_income",),
    )
    st.caption("가구 전체 기준 월평균 소득입니다. 모르는 경우 0으로 두면 결과 정확도가 낮아질 수 있습니다.")

    st.selectbox(
        "맞벌이 여부",
        ["맞벌이", "외벌이"],
        index=None,
        placeholder="맞벌이 여부를 선택하세요",
        key=widget_key("dual_income_status"),
        on_change=persist_widget,
        args=("dual_income_status",),
    )
    if st.session_state.get("dual_income_status") is None:
        st.error("맞벌이 여부는 소득 기준 판단에 필요합니다.")

    card_choice(
        "주택 구입/소유 이력",
        "has_property_history",
        PROPERTY_HISTORY_OPTIONS,
        columns=2,
    )
    if st.session_state.get("has_property_history") is None:
        st.error("생애최초 판단을 위해 주택 구입/소유 이력을 선택하세요.")

    st.number_input(
        "총자산",
        min_value=0,
        step=1000000,
        key=widget_key("total_assets", 0),
        on_change=persist_widget,
        args=("total_assets",),
    )
    st.caption("보유 예금, 투자금, 부동산 등 신청자가 판단 가능한 총자산 기준으로 입력하세요.")

    st.caption("노부모 부양 여부도 후보 판단에 사용합니다. 정확히 모르면 '모름'을 선택하세요.")
    render_detail_card_choice("elderly_support", columns=3)


def render_announcement_step() -> None:
    st.subheader("5. 공고 정보")
    st.caption("공고 정보를 입력하면 상세 시뮬레이션을 진행하고, 비워두면 현재 입력값만으로 최종 리포트를 생성합니다.")

    st.markdown("**입력 예시**")
    st.caption("예: 의왕시, 비규제지역, 민간, 59타입, 분양가 6억, 공급 120세대")
    st.caption("예: 서울 강남구 투기과열지구에 있는 민간분양 전용 84㎡ 공고이고 분양가는 15억, 공급은 300세대입니다.")
    st.text_area(
        "공고 정보를 입력해 주세요",
        placeholder="예: 서울 강남구 투기과열지구에 있는 민간분양 전용 84㎡ 공고이고 분양가는 15억, 공급은 300세대입니다.",
        height=120,
        key=widget_key("announcement_text", ""),
        on_change=persist_widget,
        args=("announcement_text",),
    )
    if not str(st.session_state.get("announcement_text") or "").strip():
        st.info("공고 정보를 비워두면 상세 공고 분석 없이 기본 리포트로 진행합니다.")


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
                st.error(error)
        if st.button("다음", disabled=bool(errors), type="primary", use_container_width=True):
            if step_key == "announcement":
                run_diagnosis(form)
            st.session_state["diagnosis_step"] = min(step_index + 1, len(STEPS) - 1)
            st.rerun()
