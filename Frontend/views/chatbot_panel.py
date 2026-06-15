"""FAQ chatbot side panel."""

from __future__ import annotations

import streamlit as st

from config.settings import load_settings
from domain.constants import RECOMMENDED_QUESTIONS
from services.api_client import ApiClientError, get_diagnosis_client



def render_chatbot_panel() -> None:
    st.markdown('<div class="cy-chat-panel">', unsafe_allow_html=True)
    st.subheader("챗봇")
    st.caption("자가진단을 보면서 궁금한 조건을 바로 물어볼 수 있습니다.")

    for index, question in enumerate(RECOMMENDED_QUESTIONS):
        if st.button(question, key=f"side_question_{index}", use_container_width=True):
            _ask(question)
            st.rerun()

    custom_question = st.text_input("직접 질문", key="chat_question_input")
    if st.button("질문하기", key="ask_custom_question", use_container_width=True):
        _ask(custom_question)
        st.rerun()

    for message in st.session_state.get("chat_messages", []):
        with st.chat_message(message["role"]):
            st.write(message["content"])
    st.markdown("</div>", unsafe_allow_html=True)


def _ask(question: str) -> None:
    if not question.strip():
        return
    st.session_state.setdefault("chat_messages", [])
    st.session_state["chat_messages"].append({"role": "user", "content": question})
    try:
        response = get_diagnosis_client().chat(question)
    except ApiClientError as exc:
        st.session_state["chat_messages"].append({
            "role": "assistant",
            "content": f"서버 연결에 실패했습니다. 잠시 후 다시 시도해주세요.\n\n오류: {exc}"
        })
        return
    answer = response["answer"]
    if response.get("sources"):
        answer = f"{answer}\n\n출처: {', '.join(response['sources'])}"
    st.session_state["session_id"] = response.get("session_id")
    st.session_state["chat_messages"].append({"role": "assistant", "content": answer})
