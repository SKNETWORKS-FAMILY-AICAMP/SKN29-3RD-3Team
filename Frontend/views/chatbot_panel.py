"""FAQ chatbot page and reusable chatbot UI."""

from __future__ import annotations

import streamlit as st

from config.settings import load_settings
from domain.constants import RECOMMENDED_QUESTIONS
from services.api_client import ApiClientError, get_diagnosis_client
from services.mock_api import MockDiagnosisClient


DEFAULT_QUESTIONS = [
    "청약통장은 꼭 있어야 하나요?",
    "무주택 기준이 뭔가요?",
    "특별공급과 일반공급 차이는 무엇인가요?",
]


def render_chatbot_page() -> None:
    st.markdown(
        """
        <div class="cy-hero-text">
          <h1>FAQ 챗봇</h1>
          <p>자가진단 중 헷갈리는 조건을 질문해보세요. '더 알아보기'에서 넘어온 질문도 이곳에서 이어집니다.</p>
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


def _render_suggested_questions(messages: list[dict[str, str]]) -> None:
    questions = RECOMMENDED_QUESTIONS if messages else DEFAULT_QUESTIONS
    st.caption("추천 질문")
    question_columns = st.columns(min(3, len(questions)))
    for index, question in enumerate(questions[:3]):
        with question_columns[index % len(question_columns)]:
            if st.button(question, key=f"chat_suggested_question_{index}_{len(messages)}", use_container_width=True):
                _ask(question)
                st.rerun()


def _render_input_form() -> None:
    with st.form("chatbot_input_form", clear_on_submit=True):
        input_col, send_col = st.columns([9, 1])
        with input_col:
            custom_question = st.text_input(
                "직접 질문",
                key="chat_question_input",
                placeholder="무엇이든 물어보세요",
                label_visibility="collapsed",
            )
        with send_col:
            submitted = st.form_submit_button("↑", use_container_width=True)
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

    answer = response["answer"]
    sources = response.get("sources") or response.get("source_refs") or []
    if sources:
        answer = f"{answer}\n\n출처: {', '.join(sources)}"
    st.session_state["chat_messages"].append({"role": "assistant", "content": answer})
