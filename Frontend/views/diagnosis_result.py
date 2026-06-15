"""Diagnosis result rendering and follow-up API actions."""

from __future__ import annotations

import streamlit as st

from components.ui import render_result
from config.settings import load_settings
from services.api_client import ApiClientError, get_diagnosis_client
from services.mock_api import MockDiagnosisClient
from services.payload import (
    DiagnosisForm,
    build_backend_compatible_payload,
    build_profile_payload,
    validate_detail_payload,
    validate_form,
)
from state.diagnosis_state import build_detail_payload, build_form_from_state


def render_result_step() -> None:
    st.subheader("5. 결과")
    form = build_form_from_state()
    errors = validate_form(form) + validate_detail_payload(build_detail_payload())
    if errors:
        st.error("필수 입력값이 부족합니다. 이전 단계로 돌아가 입력을 확인하세요.")
        for error in errors:
            st.markdown(f"- {error}")
        return

    if "last_diagnosis_response" not in st.session_state:
        run_diagnosis(form)

    if st.button("자가진단 다시 실행", use_container_width=True):
        run_diagnosis(form)
        st.rerun()

    render_result(st.session_state["last_diagnosis_response"])
    with st.expander("개발자 확인용 payload"):
        st.markdown("API 상태")
        st.json(
            {
                "mode": st.session_state.get("last_api_mode"),
                "base_url": load_settings().api_base_url,
                "error": st.session_state.get("last_api_error"),
            }
        )
        st.markdown("프로필 payload")
        st.json(st.session_state.get("last_profile_payload"))
        st.markdown("백엔드 호환 payload")
        st.json(st.session_state.get("last_backend_payload"))
        st.markdown("초기 상세 입력 payload")
        st.json(st.session_state.get("last_detail_payload"))


def run_diagnosis(form: DiagnosisForm) -> None:
    detail_payload = build_detail_payload()
    backend_payload = build_backend_compatible_payload(form, detail_payload)
    st.session_state["last_detail_payload"] = detail_payload
    st.session_state["last_profile_payload"] = build_profile_payload(form)
    st.session_state["last_backend_payload"] = backend_payload
    settings = load_settings()
    st.session_state["last_api_mode"] = settings.api_mode
    st.session_state["last_api_error"] = None

    try:
        response = get_diagnosis_client().diagnose(backend_payload)
    except ApiClientError as exc:
        fallback_response = MockDiagnosisClient().diagnose(backend_payload)
        fallback_response.setdefault("warnings", [])
        fallback_response["warnings"].insert(
            0,
            "FastAPI 연결에 실패해 mock 응답으로 대체했습니다.",
        )
        st.session_state["last_api_error"] = str(exc)
        st.session_state["last_api_mode"] = "mock_fallback"
        response = fallback_response
    else:
        if settings.api_mode == "auto":
            st.session_state["last_api_mode"] = "auto_http"

    st.session_state["last_diagnosis_response"] = response
    st.session_state.pop("last_detail_response", None)
