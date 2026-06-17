"""FAQ 챗봇 화면과 재사용 가능한 챗봇 UI.

흐름:
1. 추천 질문/직접 질문을 받아 `/api/chat`에 전달한다.
2. 백엔드 응답의 answer와 sources를 분리해 세션에 저장한다.
3. 답변 본문은 읽기 좋게 보여주고, 출처는 중복 제거 후 `참고한 자료` 영역에 따로 표시한다.
"""

from __future__ import annotations

from collections.abc import Iterable
from html import escape
import re

import streamlit as st

from config.settings import load_settings
from domain.constants import RECOMMENDED_QUESTIONS
from services.api_client import ApiClientError, get_diagnosis_client
from services.mock_api import MockDiagnosisClient


DEFAULT_QUESTIONS = [
    "청약통장은 꼭 있어야 하나요?",
    "무주택 기준은 뭔가요?",
    "특별공급과 일반공급 차이는 무엇인가요?",
]


def render_chatbot_page() -> None:
    st.markdown(
        """
        <div class="cy-hero-text">
          <h1>FAQ 챗봇</h1>
          <p>자가진단 중 헷갈리는 조건을 질문해보세요. 진단 화면의 더 자세히 물어보기 질문도 이곳에서 이어집니다.</p>
        </div>
        <div class="cy-hero-divider"></div>
        """,
        unsafe_allow_html=True,
    )
    render_chatbot_panel()


def render_chatbot_panel() -> None:
    messages = st.session_state.setdefault("chat_messages", [])
    pending_question = st.session_state.pop("pending_chat_question", None)
    if pending_question:
        messages.append({"role": "user", "content": str(pending_question)})

    with st.container(border=True):
        _render_message_area(messages)
        _render_suggested_questions(messages)
        _render_input_form()

    if pending_question:
        with st.spinner("답변을 가져오는 중입니다..."):
            _ask(str(pending_question), append_user=False)
        st.rerun()


def _render_message_area(messages: list[dict[str, str]]) -> None:
    message_box = st.container(height=560, border=True)
    with message_box:
        if not messages:
            st.markdown(
                '<div class="cy-chat-empty">추천 질문을 선택하거나 직접 입력하면 이 영역에 답변이 표시됩니다.</div>',
                unsafe_allow_html=True,
            )
        for message in messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                if message["role"] == "assistant":
                    _render_sources(message.get("sources", []))


def _render_suggested_questions(messages: list[dict[str, str]]) -> None:
    questions = RECOMMENDED_QUESTIONS if messages else DEFAULT_QUESTIONS
    st.caption("추천 질문")
    question_columns = st.columns(min(3, len(questions)))
    for index, question in enumerate(questions[:3]):
        with question_columns[index % len(question_columns)]:
            if st.button(
                question,
                key=f"chat_suggested_question_{index}_{len(messages)}",
                use_container_width=True,
            ):
                _ask(question)
                st.rerun()


def _render_input_form() -> None:
    with st.form("chatbot_input_form", clear_on_submit=True):
        input_col, send_col = st.columns([9, 1])
        with input_col:
            custom_question = st.text_input(
                "직접 질문",
                key="chat_question_input",
                placeholder="무엇이든 물어보세요.",
                label_visibility="collapsed",
            )
        with send_col:
            submitted = st.form_submit_button("전송", use_container_width=True)
        if submitted:
            _ask(custom_question)
            st.rerun()


def _ask(question: str, *, append_user: bool = True) -> None:
    if not question.strip():
        return

    st.session_state.setdefault("chat_messages", [])
    if append_user:
        st.session_state["chat_messages"].append({"role": "user", "content": question})

    settings = load_settings()
    st.session_state["last_api_mode"] = settings.api_mode
    st.session_state["last_api_error"] = None

    session_id = st.session_state.get("chat_session_id")
    try:
        response = get_diagnosis_client().chat(question, session_id=session_id)
    except ApiClientError as exc:
        response = MockDiagnosisClient().chat(question, session_id=session_id)
        response["answer"] = (
            "FastAPI 연결 실패로 mock 응답을 표시합니다.\n\n"
            f"{response['answer']}"
        )
        st.session_state["last_api_error"] = str(exc)
        st.session_state["last_api_mode"] = "mock_fallback"
    else:
        if settings.api_mode == "auto":
            st.session_state["last_api_mode"] = "auto_http"

    if response.get("session_id"):
        st.session_state["chat_session_id"] = response["session_id"]

    answer, inline_sources = _split_answer_and_inline_sources(response["answer"])
    sources = _normalize_sources(
        [
            *(response.get("sources") or []),
            *(response.get("source_refs") or []),
            *inline_sources,
        ]
    )
    st.session_state["chat_messages"].append(
        {"role": "assistant", "content": answer, "sources": sources}
    )


def _split_answer_and_inline_sources(answer: str) -> tuple[str, list[str]]:
    """답변 본문에 섞여 들어온 `출처:` 라인을 분리한다."""
    source_pattern = re.compile(r"^\s*(?:출처|참고\s*자료)\s*[:：]\s*(.+)\s*$")
    body_lines: list[str] = []
    sources: list[str] = []

    for line in str(answer).splitlines():
        match = source_pattern.match(line)
        if match:
            sources.extend(_split_source_text(match.group(1)))
            continue
        body_lines.append(line)

    cleaned_answer = "\n".join(body_lines).strip()
    return cleaned_answer or str(answer).strip(), sources


def _split_source_text(source_text: str) -> list[str]:
    """쉼표로 이어진 출처 문자열을 개별 출처 후보로 나눈다."""
    return [item.strip() for item in source_text.split(",") if item.strip()]


def _normalize_sources(raw_sources: Iterable[object]) -> list[str]:
    """출처를 사람이 읽기 좋은 짧은 라벨로 정리하고 중복을 제거한다."""
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_source in raw_sources:
        label = _format_source_label(raw_source)
        if not label or label in seen:
            continue
        seen.add(label)
        normalized.append(label)
    return normalized


def _format_source_label(raw_source: object) -> str:
    """백엔드/Mock 응답의 다양한 출처 형태를 UI용 라벨로 변환한다."""
    if isinstance(raw_source, dict):
        raw_source = raw_source.get("label") or raw_source.get("source") or ""

    label = str(raw_source).strip()
    if not label:
        return ""

    label = re.sub(r"\s+", " ", label)
    label = label.replace("청약Home", "청약홈")
    label = label.replace(" - ", " > ")
    label = label.replace(">", " > ")
    label = re.sub(r"\s*>\s*", " > ", label)
    return label[:90] + "..." if len(label) > 90 else label


def _render_sources(sources: object) -> None:
    """답변 하단에 출처를 접을 수 있는 참고자료 영역으로 표시한다."""
    normalized_sources = _normalize_sources(sources if isinstance(sources, list) else [])
    if not normalized_sources:
        return

    with st.expander("참고한 자료", expanded=False):
        chips = "".join(
            f'<span class="cy-source-chip">{escape(source)}</span>'
            for source in normalized_sources
        )
        st.markdown(f'<div class="cy-source-list">{chips}</div>', unsafe_allow_html=True)
