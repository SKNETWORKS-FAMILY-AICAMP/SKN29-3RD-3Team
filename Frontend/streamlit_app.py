from __future__ import annotations

from components.ui import (
    render_app_header,
    render_home_screen,
    render_sidebar,
    set_page_style,
)


def main() -> None:
    set_page_style()
    render_sidebar("home")
    render_app_header()
    render_home_screen()


if __name__ == "__main__":
    main()
