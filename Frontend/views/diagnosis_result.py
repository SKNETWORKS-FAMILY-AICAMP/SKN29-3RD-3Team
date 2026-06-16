"""Diagnosis result rendering and follow-up API actions."""

from __future__ import annotations

from typing import Any

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
    st.subheader("6. 결과")
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
        st.markdown("최종 응답")
        st.json(response)


def run_diagnosis(form: DiagnosisForm) -> None:
    detail_payload = build_detail_payload()
    backend_payload = build_backend_compatible_payload(form, detail_payload)
    wants_detailed = bool(st.session_state.get("wants_detailed_diagnosis_choice"))
    announcement_text = build_announcement_payload() if wants_detailed else None
    backend_payload["wants_detailed_diagnosis"] = "예" if wants_detailed else "아니오"
    if announcement_text:
        backend_payload["announcement_text"] = announcement_text
    st.session_state["last_detail_payload"] = detail_payload
    st.session_state["last_profile_payload"] = build_profile_payload(form)
    st.session_state["last_backend_payload"] = backend_payload
    settings = load_settings()
    st.session_state["last_api_mode"] = settings.api_mode
    st.session_state["last_api_error"] = None

    try:
        client = get_diagnosis_client()
        response = client.diagnose(backend_payload)
        session_id = response.get("session_id")
        if session_id:
            st.session_state["last_diagnosis_session_id"] = session_id
            st.session_state["last_simulate_response"] = client.simulate(
                session_id,
                wants_detailed,
            )
            if wants_detailed and announcement_text:
                response = client.announcement(session_id, announcement_text)
            else:
                response = st.session_state["last_simulate_response"]
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


def render_langgraph_result(response: dict[str, Any]) -> None:
    report = _report_from_response(response)
    node5 = response.get("node5") if isinstance(response.get("node5"), dict) else {}
    if not report and not node5 and not response.get("node2"):
        return

    with st.expander("상세 근거 보기", expanded=False):
        _render_supply_rank(response, report)
        _render_announcement(report, response)
        _render_finance(report, node5)
        _render_strategy(report, node5)


def _report_from_response(response: dict[str, Any]) -> dict[str, Any]:
    report = response.get("report")
    if isinstance(report, dict) and report:
        return report
    node6 = response.get("node6")
    if isinstance(node6, dict) and isinstance(node6.get("final_report"), dict):
        return node6["final_report"]
    return {}


def _render_recommendation(response: dict[str, Any], report: dict[str, Any]) -> None:
    recommended = (
        report.get("recommended_supply")
        or response.get("recommended_supply")
        or (response.get("node2") or {}).get("recommended_supply")
    )
    report_type = report.get("report_type") or response.get("result_mode")
    if not recommended and not report_type:
        return

    st.markdown("### 추천 및 자격 요약")
    cols = st.columns(3)
    cols[0].metric("추천 공급유형", recommended or "-")
    cols[1].metric("리포트 유형", _report_type_label(report_type))
    cols[2].metric("처리 상태", response.get("result_status", "-"))


SCORE_BREAKDOWN_LABELS = {
    "income": "소득 기준",
    "minor_child_count": "미성년 자녀 수",
    "residence_period_years": "거주 기간",
    "bankbook_payments": "청약통장 납입 횟수",
    "marriage_period": "혼인 기간",
    "homeless_period_years": "무주택 기간",
    "bankbook_joined_months": "청약통장 가입 기간",
    "youngest_child_age_group": "가장 어린 자녀 연령",
    "homeless_score": "무주택기간 점수",
    "dependent_family_score": "부양가족 점수",
    "subscription_score": "청약통장 가입기간 점수",
    "spouse_subscription_score": "배우자 청약통장 가입기간 점수",
}


def _render_supply_rank(response: dict[str, Any], report: dict[str, Any]) -> None:
    supply_rank = report.get("supply_rank") or response.get("supply_rank") or []
    if not supply_rank:
        node2 = response.get("node2") or {}
        supply_rank = (
            node2.get("ranked_supplies")
            or ((node2.get("supply_analysis") or {}).get("ranked_supplies") or [])
            or ((node2.get("supply_analysis") or {}).get("available_supplies") or [])
        )
    if not supply_rank:
        return

    st.markdown("#### 공급유형별 결과")
    for item in supply_rank:
        if not isinstance(item, dict):
            continue
        score = item.get("score")
        max_score = item.get("max_score")
        score_label = f"{score}/{max_score}점" if score is not None and max_score is not None else "추정 또는 별도 기준"
        with st.container(border=True):
            st.markdown(f"**{item.get('rank')}순위 — {item.get('type', '공급 유형')}** ({score_label})")
            if item.get("reason"):
                st.caption(item["reason"])

            score_breakdown = item.get("score_breakdown") or {}
            if score_breakdown:
                st.markdown("점수 산출 근거")
                for key, value in score_breakdown.items():
                    label = SCORE_BREAKDOWN_LABELS.get(key, key)
                    st.markdown(f"- {label}: {value}점")

            missing_items = item.get("missing_items") or []
            if missing_items:
                st.markdown("부족/확인 필요 항목")
                for missing in missing_items:
                    st.markdown(f"- {missing}")

            source_refs = item.get("source_refs") or []
            if source_refs:
                st.caption("출처: " + ", ".join(source_refs))


def _render_announcement(report: dict[str, Any], response: dict[str, Any]) -> None:
    announcement = report.get("announcement") or response.get("announcement") or {}
    if not isinstance(announcement, dict) or not announcement:
        return
    st.markdown("#### 공고 분석")
    cols = st.columns(4)
    cols[0].metric("지역", announcement.get("region") or "-")
    cols[1].metric("공급유형", announcement.get("supply_type") or "-")
    cols[2].metric("면적", str(announcement.get("area") or "-"))
    cols[3].metric("공급 세대", str(announcement.get("supply_count") or "-"))


def _render_finance(report: dict[str, Any], node5: dict[str, Any]) -> None:
    finance = report.get("finance") if isinstance(report.get("finance"), dict) else {}
    loan = node5.get("loan_result") if isinstance(node5.get("loan_result"), dict) else {}
    investment = (
        node5.get("investment_result")
        if isinstance(node5.get("investment_result"), dict)
        else {}
    )
    risk = node5.get("risk_result") if isinstance(node5.get("risk_result"), dict) else {}

    price = finance.get("price") or investment.get("price")
    loan_amount = finance.get("loan_amount") or loan.get("loan_amount")
    real_investment = finance.get("real_investment") or investment.get("real_investment")
    risk_level = finance.get("risk_level") or risk.get("risk_level")
    risk_description = finance.get("risk_description") or risk.get("description")

    if not any([price, loan_amount, real_investment, risk_level, risk_description]):
        return

    st.markdown("#### 재무 분석")
    cols = st.columns(4)
    cols[0].metric("분양가", _money(price))
    cols[1].metric("대출 가능액", _money(loan_amount))
    cols[2].metric("실투자금", _money(real_investment))
    cols[3].metric("자금 리스크", risk_level or "-")
    if risk_description:
        st.caption(str(risk_description))


def _render_strategy(report: dict[str, Any], node5: dict[str, Any]) -> None:
    summary = report.get("summary")
    strategy = report.get("strategy") or node5.get("agent_result")
    if summary:
        st.markdown("#### 최종 리포트")
        st.write(summary)
    if strategy:
        with st.expander("전략 분석 원문", expanded=False):
            st.write(strategy)


def _report_type_label(value: Any) -> str:
    if value == "detailed":
        return "공고 상세"
    if value == "simple":
        return "기본"
    return str(value or "-")


def _money(value: Any) -> str:
    if isinstance(value, (int, float)):
        amount = int(value)
        if amount >= 100_000_000:
            major = amount / 100_000_000
            if major.is_integer():
                return f"{int(major)}억 원"
            return f"{major:.1f}억 원"
        if amount >= 10_000:
            return f"{amount // 10_000:,}만 원"
        return f"{amount:,}원"
    return "-"
