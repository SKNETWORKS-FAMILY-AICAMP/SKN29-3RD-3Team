from __future__ import annotations

import streamlit as st

from components.ui import render_app_header, set_page_style
from views.chatbot_panel import render_chatbot_panel


def main() -> None:
    set_page_style()
    render_app_header()
    st.info("메인 자가진단 화면 오른쪽에도 같은 챗봇이 배치되어 있습니다.")
    render_chatbot_panel()


if __name__ == "__main__":
    main()
