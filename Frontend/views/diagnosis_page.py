"""Top-level diagnosis workspace layout."""

from __future__ import annotations

import streamlit as st

from config.settings import load_settings
from state.diagnosis_state import STEPS
from views.chatbot_panel import render_chatbot_panel
from views.diagnosis_result import render_result_step
from views.diagnosis_steps import (
    render_account_step,
    render_family_step,
    render_housing_step,
    render_navigation,
    render_optional_step,
    render_stepper,
)


def render_diagnosis_workspace() -> None:
    guide_col, chat_col = st.columns([2, 1], gap="large")

    with guide_col:
        render_self_diagnosis_guide()

    with chat_col:
        render_chatbot_panel()


def render_self_diagnosis_guide() -> None:
    st.session_state.setdefault("diagnosis_step", 0)
    step_index = int(st.session_state["diagnosis_step"])
    step_key, _ = STEPS[step_index]

    st.markdown(
        """
        <div class="cy-guide">
          <strong>자가진단 가이드</strong><br/>
          필수 조건을 단계별로 입력합니다. 선택 정보는 비워두고 결과로 넘어갈 수 있습니다.
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_api_status()
    render_stepper(step_index)

    if step_key == "account":
        render_account_step()
    elif step_key == "housing":
        render_housing_step()
    elif step_key == "family":
        render_family_step()
    elif step_key == "optional":
        render_optional_step()
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
