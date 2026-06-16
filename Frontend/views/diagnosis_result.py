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
from state.diagnosis_state import (
    build_announcement_payload,
    build_detail_payload,
    build_form_from_state,
)


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

    response = st.session_state["last_diagnosis_response"]
    render_result(response)
    render_langgraph_result(response)
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
    announcement_payload = build_announcement_payload()
    if announcement_payload:
        backend_payload["wants_detailed_diagnosis"] = "예"
        backend_payload["announcement"] = announcement_payload
    else:
        backend_payload["wants_detailed_diagnosis"] = "아니오"
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


def render_announcement_simulation() -> None:
    backend_payload = st.session_state.get("last_backend_payload")
    if not isinstance(backend_payload, dict) or "profile" not in backend_payload:
        return

    st.markdown("### 공고 기준 상세 시뮬레이션")
    with st.expander("공고문 정보 입력", expanded=False):
        profile = backend_payload.get("profile", {})
        default_region = str(profile.get("region") or "")

        col_1, col_2 = st.columns(2)
        with col_1:
            region = st.text_input("공고 지역", value=default_region, key="announcement_region")
            supply_type = st.selectbox(
                "공급 유형",
                ["PRIVATE", "PUBLIC", "UNKNOWN"],
                index=0,
                key="announcement_supply_type",
            )
            area = st.text_input("평형/면적", value="84", key="announcement_area")
        with col_2:
            is_regulated = st.checkbox("규제지역", value=True, key="announcement_is_regulated")
            price = st.number_input(
                "분양가",
                min_value=0,
                step=10000000,
                value=500000000,
                key="announcement_price",
            )
            supply_count = st.number_input(
                "공급 세대수",
                min_value=0,
                step=1,
                value=80,
                key="announcement_supply_count",
            )

        deposit = st.number_input(
            "보증금/계약금(선택)",
            min_value=0,
            step=1000000,
            value=0,
            key="announcement_deposit",
        )

        if st.button("공고 기준 상세 진단 실행", type="primary", use_container_width=True):
            payload = {
                **backend_payload,
                "wants_detailed_diagnosis": "예",
                "announcement": {
                    "region": region,
                    "is_regulated": bool(is_regulated),
                    "supply_type": supply_type,
                    "price": int(price),
                    "deposit": int(deposit) if int(deposit) > 0 else None,
                    "area": area,
                    "supply_count": int(supply_count),
                },
            }
            st.session_state["last_backend_payload"] = payload
            _run_detail_diagnosis(payload)
            st.rerun()


def _run_detail_diagnosis(payload: dict) -> None:
    settings = load_settings()
    st.session_state["last_api_mode"] = settings.api_mode
    st.session_state["last_api_error"] = None

    try:
        response = get_diagnosis_client().diagnose(payload)
    except ApiClientError as exc:
        fallback_response = MockDiagnosisClient().diagnose(payload)
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


def render_langgraph_result(response: dict) -> None:
    if not response.get("node2"):
        return

    node1 = response.get("node1") or {}
    node2 = response.get("node2") or {}
    node3 = response.get("node3") or {}
    node5 = response.get("node5") or {}
    node6 = response.get("node6") or {}
    report = node6.get("final_report") or {}

    st.markdown("### LangGraph 진단 요약")
    cols = st.columns(3)
    cols[0].metric("추천 유형", node2.get("recommended_supply", "-"))
    cols[1].metric("상세 경로", node3.get("route", "-"))
    cols[2].metric("검토 필요", "예" if node1.get("node1_need_review") else "아니오")

    available = node1.get("node1_available_supply_types") or []
    if available:
        st.markdown("#### 지원 가능 공급 유형")
        st.write(", ".join(str(item) for item in available))

    available_supplies = (
        node2.get("ranked_supplies")
        or ((node2.get("supply_analysis") or {}).get("ranked_supplies") or [])
        or ((node2.get("supply_analysis") or {}).get("available_supplies") or [])
    )
    if available_supplies:
        st.markdown("#### 공급 유형별 추천 순위")
        st.dataframe(available_supplies, use_container_width=True)

    if node2.get("recommendation_reason"):
        st.markdown("#### 추천 사유")
        st.write(node2["recommendation_reason"])

    if node5:
        st.markdown("#### 상세 공고 기반 자금 분석")
        announcement = (response.get("node4") or {}).get("announcement") or report.get("announcement") or {}
        loan = node5.get("loan_result") or {}
        investment = node5.get("investment_result") or {}
        risk = node5.get("risk_result") or {}
        cols = st.columns(4)
        cols[0].metric("분양가", _money(announcement.get("price") or investment.get("price")))
        cols[1].metric("대출 가능액", _money(loan.get("loan_amount")))
        cols[2].metric("실투자금", _money(investment.get("real_investment")))
        cols[3].metric("자금 리스크", risk.get("risk_level", "-"))

    if report.get("summary"):
        st.markdown("#### 최종 리포트")
        st.write(report["summary"])


def _money(value) -> str:
    if isinstance(value, int):
        return f"{value:,}원"
    return "-"
