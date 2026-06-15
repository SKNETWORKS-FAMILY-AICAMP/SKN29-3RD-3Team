from __future__ import annotations

from components.ui import render_app_header, set_page_style
from views.diagnosis_page import render_diagnosis_workspace


def main() -> None:
    set_page_style()
    render_app_header()
    render_diagnosis_workspace()


if __name__ == "__main__":
    main()
