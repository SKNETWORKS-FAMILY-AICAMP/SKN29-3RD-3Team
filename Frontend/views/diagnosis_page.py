"""Top-level diagnosis workspace layout.

테스트 메모:
- 이 워크벤치는 origin/final을 그대로 확인하기 위한 용도다.
- 아래 디버그 프리셋은 반복 입력을 줄이기 위한 임시 기능이며, 확인 후 삭제하면 된다.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from config.settings import load_settings
from state.diagnosis_state import STEPS, detail_widget_key, widget_key
from views.diagnosis_result import render_result_step
from views.diagnosis_steps import (
    render_account_step,
    render_announcement_step,
    render_family_step,
    render_housing_step,
    render_navigation,
    render_optional_step,
    render_stepper,
)


def render_diagnosis_workspace() -> None:
    render_self_diagnosis_guide()


def render_self_diagnosis_guide() -> None:
    st.session_state.setdefault("diagnosis_step", 0)
    step_index = int(st.session_state["diagnosis_step"])
    step_key, _ = STEPS[step_index]

    st.markdown(
        """
        <div class="cy-guide">
          <strong>자가진단 가이드</strong>
          필수 조건을 순서대로 입력하면 진단을 진행할 수 있습니다.
          공고 정보는 비워두면 기본 리포트로, 입력하면 공고 기준 상세 리포트로 이어집니다.
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_debug_preset_button()
    render_stepper(step_index)

    with st.container(border=True):
        if step_key == "account":
            render_account_step()
        elif step_key == "housing":
            render_housing_step()
        elif step_key == "family":
            render_family_step()
        elif step_key == "optional":
            render_optional_step()
        elif step_key == "announcement":
            render_announcement_step()
        elif step_key == "result":
            render_result_step()

    render_navigation(step_index)


def render_api_status() -> None:
    settings = load_settings()
    if settings.api_mode == "auto":
        st.caption(f"API 모드: auto ({settings.api_base_url}, 실패 시 mock)")
    elif settings.api_mode == "http":
        st.caption(f"API 모드: http ({settings.api_base_url})")
    else:
        st.caption("API 모드: mock")


def _render_debug_preset_button() -> None:
    """반복 테스트용 임시 버튼."""
    with st.expander("디버그 입력 프리셋", expanded=False):
        st.caption("테스트용 임시 기능입니다. 입력값을 채우고 결과 단계로 바로 이동합니다.")
        if st.button("테스트 입력값 채우고 결과 보기", use_container_width=True):
            _apply_debug_preset()
            st.rerun()


def _apply_debug_preset() -> None:
    """final 백엔드 결과 화면 확인용 대표 입력값을 session_state에 주입한다."""
    preset = {
        "bankbook_type": "주택청약종합저축",
        "bankbook_join_date": date(2024, 1, 1),
        "bankbook_payments": 24,
        "bankbook_balance": 10_000_000,
        "region": "서울",
        "residence_period_years": 5,
        "is_homeless": True,
        "homeless_period_years": 4,
        "is_household_head": True,
        "num_household_members": 4,
        "birth_year": 1990,
        "marital_status": "MARRIED",
        "marriage_period_years": 0,
        "child_status": "HAS_CHILD",
        "minor_child_count": 2,
        "dual_income_status": "외벌이",
        "average_monthly_income": 5_000_000,
        "has_property_history": False,
        "total_assets": 100_000_000,
        "wants_detailed_diagnosis_choice": True,
        "announcement_text": "서울 강남구, 투기과열지구, 민간, 전용 84㎡, 분양가 5억, 공급 80세대",
    }
    detail_preset = {
        "youngest_child_age_group": "AGE_2_TO_6",
        "child_count_group": "TWO_OR_MORE",
        "housing_history": "NO_HISTORY",
        "elderly_support": "DOES_NOT_MEET",
    }

    for key, value in preset.items():
        st.session_state[key] = value
        st.session_state[widget_key(key)] = value
    for key, value in detail_preset.items():
        st.session_state[detail_widget_key(key)] = value

    st.session_state["diagnosis_step"] = len(STEPS) - 1
    for key in (
        "last_diagnosis_response",
        "last_detail_response",
        "last_simulate_response",
        "last_diagnosis_session_id",
    ):
        st.session_state.pop(key, None)
