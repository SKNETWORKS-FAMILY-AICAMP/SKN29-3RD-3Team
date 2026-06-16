"""Shared Streamlit UI helpers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import streamlit as st

from config.settings import load_settings
from services.api_client import check_api_connection


CHATBOT_PAGE = "pages/2_FAQ_챗봇.py"
DIAGNOSIS_PAGE = "pages/1_청약_자가진단.py"
HOME_PAGE = "streamlit_app.py"


def set_page_style() -> None:
    st.set_page_config(page_title="청약 자가진단", page_icon="🏠", layout="wide")
    st.markdown(
        """
        <style>
        :root {
            --cy-navy: #172033;
            --cy-blue: #2558a8;
            --cy-blue-soft: #eef4ff;
            --cy-line: #d8e0ee;
            --cy-muted: #667085;
            --cy-bg: #f6f8fb;
        }
        .stApp {
            background: linear-gradient(180deg, #ffffff 0%, #f7f9fc 62%, #f4f7fb 100%);
        }
        .block-container {
            max-width: 1120px;
            padding-top: 1.05rem;
            padding-bottom: 4rem;
        }
        .cy-hero-divider {
            border-bottom: 1px solid var(--cy-line);
            padding-bottom: .9rem;
            margin-bottom: 1.1rem;
        }
        .cy-hero-text h1 {
            margin: 0 0 .4rem;
            color: var(--cy-navy);
            font-size: 2.15rem;
            line-height: 1.2;
            letter-spacing: 0;
        }
        .cy-hero-text p {
            color: var(--cy-muted);
            margin: 0;
            font-size: 1.02rem;
            line-height: 1.55;
        }
        .cy-home {
            padding: 2.2rem 0 1.35rem;
        }
        .cy-home h2 {
            margin: 0 0 .8rem;
            color: var(--cy-navy);
            font-size: 2.35rem;
            line-height: 1.18;
            letter-spacing: 0;
        }
        .cy-home p {
            max-width: 720px;
            color: #475467;
            font-size: 1.05rem;
            line-height: 1.7;
        }
        .cy-feature-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: .8rem;
            margin: 1.5rem 0 1.25rem;
        }
        .cy-feature {
            border: 1px solid var(--cy-line);
            border-radius: 8px;
            padding: 1rem;
            background: #ffffff;
            box-shadow: 0 8px 22px rgba(24, 40, 72, .05);
        }
        .cy-feature strong {
            display: block;
            margin-bottom: .35rem;
            color: var(--cy-navy);
        }
        .cy-feature span {
            color: var(--cy-muted);
            font-size: .92rem;
            line-height: 1.5;
        }
        .cy-guide {
            border: 1px solid var(--cy-line);
            border-radius: 8px;
            padding: .95rem 1.05rem;
            background: #ffffff;
            margin-bottom: .8rem;
            color: #344054;
            box-shadow: 0 8px 22px rgba(24, 40, 72, .05);
        }
        .cy-guide strong {
            display: block;
            color: var(--cy-navy);
            margin-bottom: .25rem;
        }
        .cy-stepper {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: .4rem;
            margin: .75rem 0 1rem;
        }
        .cy-step {
            display: inline-flex;
            align-items: center;
            min-height: 2.05rem;
            padding: .35rem .68rem;
            border: 1px solid var(--cy-line);
            border-radius: 999px;
            color: #8a94a6;
            background: #ffffff;
            font-size: .88rem;
            line-height: 1.2;
        }
        .cy-step-active {
            border-color: var(--cy-blue);
            color: #12356f;
            background: var(--cy-blue-soft);
            font-weight: 800;
            box-shadow: 0 5px 14px rgba(37, 88, 168, .13);
        }
        .cy-step-arrow {
            color: #b7c0d0;
            font-size: .85rem;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--cy-line);
            border-radius: 8px;
            box-shadow: 0 8px 22px rgba(24, 40, 72, .05);
            background: #ffffff;
        }
        div.stButton > button {
            min-height: 2.65rem;
            white-space: normal;
            border-radius: 8px;
        }
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        textarea {
            border-radius: 8px;
        }
        [data-testid="stSidebarNav"],
        section[data-testid="stSidebar"] nav,
        section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] {
            display: none !important;
        }
        @media (max-width: 760px) {
            .cy-feature-row {
                grid-template-columns: 1fr;
            }
            .cy-home h2 {
                font-size: 1.85rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_app_header() -> None:
    title_col, beta_col = st.columns([8.5, 1.5])
    with title_col:
        st.markdown(
            """
            <div class="cy-hero-text">
            <h1>청약 자가진단</h1>
            <p>내 조건을 입력하면 가능한 공급 유형과 추가 확인이 필요한 항목을 한 화면에서 확인할 수 있어요.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with beta_col:
        settings = load_settings()
        if hasattr(st, "popover"):
            with st.popover("Beta", use_container_width=True):
                st.caption("현재는 로컬 FastAPI와 연결을 검증 중인 베타 화면입니다.")
                st.caption(f"API: {settings.api_mode} / {settings.api_base_url}")
        else:
            with st.expander("Beta", expanded=False):
                st.caption("현재는 로컬 FastAPI와 연결을 검증 중인 베타 화면입니다.")
                st.caption(f"API: {settings.api_mode} / {settings.api_base_url}")
    st.markdown('<div class="cy-hero-divider"></div>', unsafe_allow_html=True)


def render_home_screen() -> None:
    st.markdown(
        """
        <section class="cy-home">
          <h2>청약 조건을 먼저 정리해 보세요</h2>
          <p>
            통장, 무주택, 세대, 혼인, 자녀, 소득과 자산 조건을 단계별로 입력하면
            지원 가능성이 있는 공급 유형과 공고 기준 추가 확인 항목을 볼 수 있습니다.
          </p>
          <div class="cy-feature-row">
            <div class="cy-feature">
              <strong>자가진단</strong>
              <span>필수 조건을 단계별로 입력하고 결과를 확인합니다.</span>
            </div>
            <div class="cy-feature">
              <strong>공고 정보</strong>
              <span>공고문 줄글을 입력하면 백엔드 Node4가 구조화해 상세 시뮬레이션으로 이어갑니다.</span>
            </div>
            <div class="cy-feature">
              <strong>FAQ 챗봇</strong>
              <span>진단 중 궁금한 청약 기준을 바로 질문할 수 있습니다.</span>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if st.button("자가진단하러 가기", type="primary", use_container_width=False):
        st.switch_page(DIAGNOSIS_PAGE)


def render_sidebar(active_page: str) -> None:
    with st.sidebar:
        st.markdown("### 청약 도우미")
        st.caption("모드 전환")
        _sidebar_page_link(HOME_PAGE, "처음 화면", active=active_page == "home")
        _sidebar_page_link(DIAGNOSIS_PAGE, "자가진단", active=active_page == "diagnosis")
        _sidebar_page_link(CHATBOT_PAGE, "FAQ 챗봇", active=active_page == "chatbot")
        st.divider()
        render_api_connection_status()


def render_api_connection_status() -> None:
    if st.button("API 상태 새로고침", use_container_width=True):
        _cached_api_connection_status.clear()
    status = _cached_api_connection_status()
    st.markdown("### API 연결")
    st.caption(status["base_url"])

    if status["ok"]:
        if status["mode"] == "mock":
            st.info("Mock 응답 사용 중")
        else:
            st.success(f"연결됨 ({status['mode']})")
        return

    st.error(f"연결 실패 ({status['mode']})")
    with st.expander("오류 보기", expanded=False):
        st.write(status["message"])


@st.cache_data(ttl=15, show_spinner=False)
def _cached_api_connection_status() -> dict[str, Any]:
    return check_api_connection()


def _sidebar_page_link(page: str, label: str, *, active: bool) -> None:
    marker = "●" if active else "○"
    if hasattr(st, "page_link"):
        st.page_link(page, label=f"{marker} {label}")
        return
    st.markdown(f"{marker} {label}")


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


def render_explanation(
    title: str,
    items: Sequence[str],
    *,
    learn_more_question: str | None = None,
    learn_more_key: str | None = None,
) -> None:
    with st.expander(title, expanded=False):
        for item in items:
            st.markdown(f"- {item}")
        if learn_more_question:
            button_key = learn_more_key or f"learn_more_{abs(hash(learn_more_question))}"
            if st.button("더 자세히 물어보기", key=button_key, use_container_width=True):
                open_chatbot_with_question(learn_more_question)


def open_chatbot_with_question(question: str) -> None:
    st.session_state["pending_chat_question"] = question
    try:
        st.switch_page(CHATBOT_PAGE)
    except Exception:
        st.info("사이드바에서 FAQ 챗봇을 선택하면 이어서 확인할 수 있습니다.")


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
                        st.caption("추정 또는 별도 기준")
                    else:
                        ratio = item.get("ratio")
                        st.caption(f"{score}/{max_score}점" + (f" ({ratio})" if ratio else ""))
                    if item.get("reason"):
                        st.write(item["reason"])

    st.subheader(f"종합 상태: {response.get('result_status', '추가 확인 필요')}")
    if response.get("result_mode"):
        st.caption(f"결과 모드: {response['result_mode']}")

    for warning in response.get("warnings", []):
        st.warning(warning)

    if response.get("guide_message"):
        st.info(response["guide_message"])

    for title, key in [
        ("제한 사유", "blocked_reasons"),
        ("부족한 입력값", "missing_inputs"),
        ("공고/증빙 확인 항목", "pending_external_checks"),
        ("다음 확인 항목", "next_actions"),
    ]:
        values = response.get(key, [])
        if values:
            st.markdown(f"#### {title}")
            for value in values:
                st.markdown(f"- {value}")

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

    collected_detail_fields = response.get("collected_detail_fields", [])
    if collected_detail_fields:
        st.caption("초기 상세 입력 반영: " + ", ".join(collected_detail_fields))
