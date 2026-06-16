"""Shared Streamlit UI helpers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import streamlit as st


def set_page_style() -> None:
    st.set_page_config(page_title="청약 자가진단", page_icon="🏠", layout="wide")
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1180px;
            padding-top: 1.75rem;
            padding-bottom: 4rem;
        }
        .cy-header {
            border-bottom: 1px solid #d8e0ee;
            padding-bottom: 1rem;
            margin-bottom: 1.25rem;
        }
        .cy-header h1 {
            margin: 0 0 .35rem;
            color: #1f2937;
            font-size: 2rem;
            letter-spacing: 0;
        }
        .cy-header p {
            color: #667085;
            margin: 0;
        }
        .cy-guide {
            border: 1px solid #d8e0ee;
            border-radius: 8px;
            padding: 1rem;
            background: #f8fafc;
            margin-bottom: 1rem;
        }
        .cy-chat-panel {
            border: 1px solid #d8e0ee;
            border-radius: 8px;
            padding: 1rem;
            background: white;
        }
        div.stButton > button {
            min-height: 2.65rem;
            white-space: normal;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_app_header() -> None:
    st.markdown(
        """
        <div class="cy-header">
          <h1>청약 자가진단</h1>
          <p>카드형 선택지로 조건을 정리하고, 오른쪽 챗봇에서 질문을 이어갑니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card_choice(
    label: str,
    key: str,
    options: Sequence[dict[str, Any]],
    *,
    columns: int = 3,
    default_value: Any = None,
    clear_result_state: bool = True,
) -> Any:
    st.markdown(f"**{label}**")
    selected_value = st.session_state.get(key, default_value)
    option_columns = st.columns(min(columns, len(options)))
    selected_label = None

    for index, option in enumerate(options):
        with option_columns[index % len(option_columns)]:
            selected = selected_value == option["value"]
            if selected:
                selected_label = option["label"]
            with st.container(border=True):
                marker = "선택됨" if selected else "선택"
                st.markdown(f"**{option['label']}**")
                if option.get("description"):
                    st.caption(option["description"])
                if st.button(
                    marker,
                    key=f"{key}_{index}_{str(option['value'])}",
                    disabled=selected,
                    type="primary" if selected else "secondary",
                    use_container_width=True,
                ):
                    st.session_state[key] = option["value"]
                    if clear_result_state:
                        st.session_state.pop("last_diagnosis_response", None)
                    st.session_state.pop("last_detail_response", None)
                    st.rerun()

    if selected_label:
        st.caption(f"현재 선택: {selected_label}")

    return st.session_state.get(key, selected_value)


def render_explanation(title: str, items: Sequence[str]) -> None:
    with st.expander(title, expanded=False):
        for item in items:
            st.markdown(f"- {item}")


def _top_supply_rank(response: dict, limit: int = 3) -> list[dict[str, Any]]:
    supply_rank = response.get("supply_rank")
    if not isinstance(supply_rank, list):
        return []
    return [item for item in supply_rank[:limit] if isinstance(item, dict)]


def render_result(response: dict) -> None:
    supply_rank = _top_supply_rank(response)
    if supply_rank:
        st.subheader("추천 순위 Top 3")
        rank_columns = st.columns(min(3, len(supply_rank)))
        for index, item in enumerate(supply_rank):
            with rank_columns[index]:
                with st.container(border=True):
                    st.markdown(f"#### {item.get('rank')}위")
                    st.markdown(f"**{item.get('type', '공급 유형')}**")
                    score = item.get("score")
                    max_score = item.get("max_score")
                    if score is None or max_score is None:
                        st.caption("추첨제/조건형")
                    else:
                        ratio = item.get("ratio")
                        st.caption(f"{score}/{max_score}점" + (f" ({ratio})" if ratio else ""))
                    if item.get("reason"):
                        st.write(item["reason"])

    if response.get("final_report"):
        st.subheader("최종 결론")
        st.markdown(response["final_report"])

    st.subheader(f"종합 상태: {response.get('result_status', '추가 확인 필요')}")
    if response.get("result_mode"):
        st.caption(f"결과 모드: {response['result_mode']}")

    for warning in response.get("warnings", []):
        st.warning(warning)

    if response.get("guide_message"):
        st.info(response["guide_message"])

    blocked_reasons = response.get("blocked_reasons", [])
    if blocked_reasons:
        st.markdown("#### 제한 사유")
        for reason in blocked_reasons:
            st.markdown(f"- {reason}")

    missing_inputs = response.get("missing_inputs", [])
    if missing_inputs:
        st.markdown("#### 부족한 입력값")
        for missing in missing_inputs:
            st.markdown(f"- {missing}")

    for item in response.get("candidate_supply_types", []):
        with st.container(border=True):
            st.markdown(f"#### {item.get('supply_type', '공급 유형')}")
            st.write(f"상태: {item.get('status', '확인 필요')}")
            if item.get("reasons"):
                st.markdown("근거")
                for reason in item["reasons"]:
                    st.markdown(f"- {reason}")
            if item.get("missing_checks"):
                st.markdown("추가 확인")
                for check in item["missing_checks"]:
                    st.markdown(f"- {check}")
            if item.get("source_refs"):
                st.caption("출처: " + ", ".join(item["source_refs"]))

    pending_external_checks = response.get("pending_external_checks", [])
    if pending_external_checks:
        st.markdown("#### 공고/증빙 확인 항목")
        for check in pending_external_checks:
            st.markdown(f"- {check}")

    collected_detail_fields = response.get("collected_detail_fields", [])
    if collected_detail_fields:
        st.caption("초기 상세 입력 반영: " + ", ".join(collected_detail_fields))
    if response.get("next_actions"):
        st.markdown("#### 다음 확인 항목")
        for action in response["next_actions"]:
            st.markdown(f"- {action}")
