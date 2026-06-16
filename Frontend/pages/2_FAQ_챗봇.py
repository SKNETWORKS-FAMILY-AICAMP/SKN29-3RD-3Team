from __future__ import annotations

from components.ui import render_sidebar, set_page_style
from views.chatbot_panel import render_chatbot_page


def main() -> None:
    set_page_style()
    render_sidebar("chatbot")
    render_chatbot_page()


if __name__ == "__main__":
    main()
