"""Shared Streamlit UI helpers."""

from __future__ import annotations

from collections.abc import Sequence
from html import escape
from typing import Any

import streamlit as st

from services.api_client import check_api_connection


CHATBOT_PAGE = "pages/2_FAQ_챗봇.py"
DIAGNOSIS_PAGE = "pages/1_청약_자가진단.py"
HOME_PAGE = "streamlit_app.py"
THEME_OPTIONS = ["라이트", "다크"]


@st.cache_resource(show_spinner=False)
def _theme_store() -> dict[str, str]:
    """Streamlit multipage 간에도 유지되는 발표용 테마 저장소."""
    return {"mode": "라이트"}


def _current_theme_mode() -> str:
    """페이지 이동 후에도 유지되도록 cache/session/query param의 테마 값을 동기화한다."""
    store = _theme_store()
    query_theme = st.query_params.get("theme")
    if query_theme in THEME_OPTIONS:
        st.session_state["theme_mode"] = query_theme
        store["mode"] = query_theme

    mode = st.session_state.get("theme_mode") or store.get("mode", "라이트")
    if mode not in THEME_OPTIONS:
        mode = "라이트"
    st.session_state["theme_mode"] = mode
    store["mode"] = mode
    return mode


def _sync_theme_query_param() -> None:
    """테마 선택값을 URL에도 남겨 Streamlit multipage 이동 시 초기화를 줄인다."""
    mode = st.session_state.get("theme_mode", "라이트")
    if mode in THEME_OPTIONS:
        _theme_store()["mode"] = mode
        st.query_params["theme"] = mode


def _theme_css() -> str:
    """사이드바 테마 선택값에 맞춰 청약 랭그래프 시스템 색상 토큰을 만든다."""
    mode = _current_theme_mode()
    light_tokens = """
        :root {
            --cy-navy: #172033;
            --cy-text: #172033;
            --cy-text-soft: #344054;
            --cy-subtext: #475467;
            --cy-muted: #667085;
            --cy-blue: #2558a8;
            --cy-blue-hover: #1f4b91;
            --cy-blue-strong: #12356f;
            --cy-blue-soft: #eef4ff;
            --cy-line: #d8e0ee;
            --cy-line-soft: #edf1f7;
            --cy-line-strong: #b8c4d8;
            --cy-bg: #f6f8fb;
            --cy-surface: #ffffff;
            --cy-surface-soft: #fbfcff;
            --cy-app-bg: linear-gradient(180deg, #ffffff 0%, #f7f9fc 62%, #f4f7fb 100%);
            --cy-on-blue: #ffffff;
            --cy-success-bg: #ecfdf3;
            --cy-success-text: #067647;
            --cy-success-line: #b7e4c7;
            --cy-warn-bg: #fff8e6;
            --cy-warn-text: #7a5200;
            --cy-warn-line: #f5d58a;
            --cy-danger-bg: #fff5f5;
            --cy-danger-text: #b04444;
            --cy-danger-strong: #8f2929;
            --cy-danger-line: #f0c7c7;
            --cy-shadow: 0 14px 34px rgba(24, 40, 72, .08);
            --cy-shadow-soft: 0 8px 22px rgba(24, 40, 72, .05);
            --cy-shadow-blue: 0 10px 22px rgba(37, 88, 168, .16);
        }
    """
    dark_tokens = """
        :root {
            --cy-navy: #f8fafc;
            --cy-text: #f8fafc;
            --cy-text-soft: #e2e8f5;
            --cy-subtext: #c4cde0;
            --cy-muted: #a8b4ca;
            --cy-blue: #8fb3ff;
            --cy-blue-hover: #aac6ff;
            --cy-blue-strong: #cfe2ff;
            --cy-blue-soft: #1b335d;
            --cy-line: #4c5d79;
            --cy-line-soft: #33425d;
            --cy-line-strong: #70819f;
            --cy-bg: #0f172a;
            --cy-surface: #1a2438;
            --cy-surface-soft: #141f33;
            --cy-app-bg: linear-gradient(180deg, #0c1424 0%, #101827 58%, #111827 100%);
            --cy-on-blue: #f8fafc;
            --cy-success-bg: #0f2f24;
            --cy-success-text: #8ee6b0;
            --cy-success-line: #245b43;
            --cy-warn-bg: #2a2414;
            --cy-warn-text: #ffd783;
            --cy-warn-line: #624c1a;
            --cy-danger-bg: #321b1b;
            --cy-danger-text: #ffaaa5;
            --cy-danger-strong: #ffc2bd;
            --cy-danger-line: #6f3331;
            --cy-shadow: 0 16px 36px rgba(0, 0, 0, .34);
            --cy-shadow-soft: 0 10px 24px rgba(0, 0, 0, .24);
            --cy-shadow-blue: 0 10px 24px rgba(110, 168, 255, .18);
        }
    """
    dark_overrides = """
        .cy-brand-logo-slot,
        .cy-home-proof span,
        .cy-preview,
        .cy-feature,
        .cy-result-hero,
        .cy-status-chip,
        .cy-next-actions,
        .cy-guide,
        .cy-step,
        .cy-source-chip,
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--cy-line-strong) !important;
            background: var(--cy-surface) !important;
            color: var(--cy-text-soft) !important;
            box-shadow: inset 0 0 0 1px rgba(126, 166, 247, .08), var(--cy-shadow-soft) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div,
        div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {
            background: transparent !important;
        }
        .cy-preview-note,
        .cy-status-chip.warn {
            border-color: var(--cy-warn-line) !important;
            background: var(--cy-warn-bg) !important;
            color: var(--cy-warn-text) !important;
        }
        .cy-preview-tag,
        .cy-status-chip.good {
            border-color: var(--cy-success-line) !important;
            background: var(--cy-success-bg) !important;
            color: var(--cy-success-text) !important;
        }
        .cy-kicker,
        .cy-badge,
        .cy-step-active {
            border-color: var(--cy-blue) !important;
            background: var(--cy-blue-soft) !important;
            color: var(--cy-blue-strong) !important;
        }
        .cy-preview-title,
        .cy-preview-row strong,
        .cy-feature strong,
        .cy-result-hero h2,
        .cy-next-actions strong,
        .cy-guide strong,
        .cy-hero-text h1,
        .cy-home h2 {
            color: var(--cy-text) !important;
        }
        .cy-home p,
        .cy-hero-text p,
        .cy-preview-row,
        .cy-result-hero p,
        .cy-next-actions ol,
        .cy-feature span {
            color: var(--cy-subtext) !important;
        }
        .cy-preview-value,
        .cy-result-kicker {
            color: var(--cy-blue) !important;
        }
        .cy-brand-logo-slot::after {
            background: var(--cy-blue) !important;
        }
        .cy-validation-summary {
            border-color: var(--cy-danger-line) !important;
            background: var(--cy-danger-bg) !important;
            color: var(--cy-danger-text) !important;
        }
        .cy-validation-summary strong {
            color: var(--cy-danger-strong) !important;
        }
        div.stButton > button[kind="primary"] {
            border-color: var(--cy-blue) !important;
            background: var(--cy-blue) !important;
            color: var(--cy-on-blue) !important;
        }
        div.stButton > button[kind="primary"] *,
        button[kind="primary"] *,
        button[data-testid="stBaseButton-primary"] * {
            color: var(--cy-on-blue) !important;
        }
        div.stButton > button[kind="primary"]:hover {
            border-color: var(--cy-blue-hover) !important;
            background: var(--cy-blue-hover) !important;
        }
        button[kind="secondaryFormSubmit"],
        button[data-testid="stBaseButton-secondaryFormSubmit"] {
            border-color: var(--cy-blue) !important;
            background: var(--cy-blue) !important;
            color: var(--cy-on-blue) !important;
        }
        button[kind="secondaryFormSubmit"] *,
        button[data-testid="stBaseButton-secondaryFormSubmit"] * {
            color: var(--cy-on-blue) !important;
        }
        div.stButton > button:not([kind="primary"]),
        div[data-testid="stButton"] button:not([kind="primary"]),
        button[kind="secondary"] {
            border-color: var(--cy-line) !important;
            background: #172238 !important;
            color: var(--cy-text-soft) !important;
        }
        div.stButton > button:not([kind="primary"]) *,
        div[data-testid="stButton"] button:not([kind="primary"]) *,
        button[kind="secondary"] * {
            color: var(--cy-text-soft) !important;
        }
        div.stButton > button:disabled,
        div[data-testid="stButton"] button:disabled,
        button:disabled {
            border-color: var(--cy-line-soft) !important;
            background: #151f32 !important;
            color: #9ca8bf !important;
            opacity: 1 !important;
        }
        header[data-testid="stHeader"],
        div[data-testid="stToolbar"],
        div[data-testid="stDecoration"] {
            background: transparent !important;
        }
        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] > div,
        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        div[data-testid="stDateInput"] input,
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        textarea {
            background-color: var(--cy-surface-soft) !important;
            color: var(--cy-text) !important;
            border-color: var(--cy-line) !important;
        }
        input::placeholder,
        textarea::placeholder,
        div[data-baseweb="select"] input::placeholder,
        div[data-baseweb="select"] input,
        div[data-baseweb="select"] > div,
        div[data-baseweb="select"] > div *,
        div[data-baseweb="select"] [role="combobox"],
        div[data-baseweb="select"] [aria-readonly="true"],
        div[data-baseweb="select"] [class*="placeholder"],
        div[data-baseweb="select"] [aria-disabled="true"],
        div[data-baseweb="select"] div[disabled],
        [data-baseweb="select"] [data-testid="stMarkdownContainer"],
        [data-baseweb="select"] span {
            color: #e5efff !important;
            -webkit-text-fill-color: #e5efff !important;
            opacity: 1 !important;
        }
        div[data-baseweb="select"] > div {
            background-color: #172238 !important;
            border-color: #70819f !important;
        }
        div[data-testid="stNumberInput"] button,
        div[data-testid="stNumberInput"] [role="button"],
        div[data-testid="stNumberInput"] button *,
        div[data-testid="stNumberInput"] [role="button"] * {
            background: #1b263a !important;
            color: #e6edf8 !important;
            fill: #e6edf8 !important;
            stroke: #e6edf8 !important;
            border-color: var(--cy-line) !important;
        }
        div[data-testid="stNumberInput"] button:disabled,
        div[data-testid="stNumberInput"] [aria-disabled="true"],
        div[data-testid="stNumberInput"] button:disabled *,
        div[data-testid="stNumberInput"] [aria-disabled="true"] * {
            color: #a6b3ca !important;
            fill: #a6b3ca !important;
            stroke: #a6b3ca !important;
            background: #151f32 !important;
        }
        div[data-baseweb="popover"],
        div[data-baseweb="popover"] > div,
        ul[role="listbox"],
        li[role="option"] {
            border-color: var(--cy-line) !important;
            background: var(--cy-surface) !important;
            color: var(--cy-text) !important;
        }
        li[role="option"]:hover,
        li[aria-selected="true"],
        div[role="option"]:hover,
        div[aria-selected="true"] {
            background: var(--cy-blue-soft) !important;
            color: var(--cy-blue-strong) !important;
        }
        div[data-baseweb="select"] svg,
        div[data-baseweb="input"] svg {
            color: var(--cy-muted) !important;
            fill: var(--cy-muted) !important;
        }
        div[data-testid="stExpander"],
        div[data-testid="stExpander"] details,
        div[data-testid="stExpander"] summary,
        div[data-testid="stExpanderDetails"],
        details,
        summary {
            border-color: var(--cy-line) !important;
            background: var(--cy-surface) !important;
            color: var(--cy-text-soft) !important;
        }
        pre,
        code,
        div[data-testid="stJson"],
        div[data-testid="stJson"] pre,
        div[data-testid="stCodeBlock"],
        div[data-testid="stCodeBlock"] pre {
            border-color: var(--cy-line) !important;
            background: #0c1424 !important;
            color: #dbe7ff !important;
        }
        div[data-testid="stChatMessage"] {
            border: 1px solid var(--cy-line) !important;
            border-radius: 8px !important;
            background: var(--cy-surface) !important;
            color: var(--cy-text-soft) !important;
        }
        div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
        div[data-testid="stChatMessage"] p,
        div[data-testid="stChatMessage"] li {
            color: var(--cy-text-soft) !important;
        }
        div[data-testid="stChatMessage"] h1,
        div[data-testid="stChatMessage"] h2,
        div[data-testid="stChatMessage"] h3,
        div[data-testid="stChatMessage"] h4,
        div[data-testid="stChatMessage"] strong {
            color: var(--cy-text) !important;
        }
        div[data-testid="stChatInput"],
        div[data-testid="stChatInput"] textarea,
        div[data-testid="stChatInput"] input {
            background: var(--cy-surface-soft) !important;
            color: var(--cy-text) !important;
            border-color: var(--cy-line) !important;
        }
        div[data-testid="stChatInput"] button {
            background: var(--cy-blue) !important;
            color: var(--cy-on-blue) !important;
            border-color: var(--cy-blue) !important;
        }
        .cy-theme-toggle {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: .25rem;
            border: 1px solid var(--cy-line);
            border-radius: 8px;
            padding: .22rem;
            background: #10192b;
        }
        .cy-theme-option {
            display: block;
            text-align: center;
            border-radius: 6px;
            padding: .42rem .5rem;
            color: var(--cy-text-soft) !important;
            text-decoration: none !important;
            font-weight: 750;
            line-height: 1.2;
        }
        .cy-theme-option.active {
            background: var(--cy-blue);
            color: var(--cy-on-blue) !important;
            box-shadow: var(--cy-shadow-blue);
        }
        div[data-testid="stChatMessage"] > div:first-child {
            background: transparent !important;
        }
        div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]),
        div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
            background: var(--cy-surface) !important;
        }
        div[data-testid="stChatMessage"] [data-testid="chatAvatarIcon-user"] {
            background: #e95555 !important;
            color: #ffffff !important;
        }
        div[data-testid="stChatMessage"] [data-testid="chatAvatarIcon-assistant"] {
            background: #f2a93b !important;
            color: #ffffff !important;
        }
        label,
        label p,
        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] p,
        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] p {
            color: var(--cy-subtext) !important;
        }
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li {
            color: var(--cy-text-soft) !important;
        }
        h1, h2, h3, h4, h5, h6,
        [data-testid="stMarkdownContainer"] strong {
            color: var(--cy-text) !important;
        }
        section[data-testid="stSidebar"] a,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] div {
            color: var(--cy-subtext) !important;
        }
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: var(--cy-text) !important;
        }
    """
    if mode == "다크":
        return dark_tokens + dark_overrides
    return light_tokens


def set_page_style() -> None:
    st.set_page_config(page_title="청약 랭그래프 시스템", page_icon="청", layout="wide")
    st.markdown(
        "<style>\n"
        + _theme_css()
        + """
        .stApp {
            background: var(--cy-app-bg);
            color: var(--cy-text);
        }
        .block-container {
            max-width: 1120px;
            padding-top: 2.7rem;
            padding-bottom: 4rem;
        }
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        #MainMenu {
            display: none !important;
        }
        .cy-hero-divider {
            border-bottom: 1px solid var(--cy-line);
            padding-bottom: .9rem;
            margin-bottom: 1.1rem;
        }
        .cy-brand {
            display: flex;
            align-items: center;
            gap: .8rem;
        }
        .cy-brand-logo-slot {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2.35rem;
            height: 2.35rem;
            border-radius: 8px;
            border: 1px dashed #b8c4d8;
            background: #f8fbff;
            box-shadow: 0 8px 18px rgba(24, 40, 72, .05);
        }
        .cy-brand-logo-slot::after {
            content: "";
            width: .82rem;
            height: .82rem;
            border-radius: 3px;
            background: #2558a8;
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
            padding: 1.7rem 0 1.35rem;
        }
        .cy-home-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.02fr) minmax(320px, .78fr);
            gap: 2rem;
            align-items: center;
        }
        .cy-kicker {
            display: inline-flex;
            align-items: center;
            min-height: 1.9rem;
            padding: .35rem .62rem;
            border-radius: 999px;
            background: #eef4ff;
            color: #2558a8;
            font-size: .86rem;
            font-weight: 750;
            margin-bottom: .85rem;
        }
        .cy-home h2 {
            margin: 0 0 .85rem;
            color: var(--cy-navy);
            font-size: 2.55rem;
            line-height: 1.12;
            letter-spacing: 0;
        }
        .cy-home p {
            max-width: 660px;
            color: #475467;
            font-size: 1.05rem;
            line-height: 1.7;
        }
        .cy-home-proof {
            display: flex;
            flex-wrap: wrap;
            gap: .45rem;
            margin-top: 1.1rem;
        }
        .cy-home-proof span {
            display: inline-flex;
            align-items: center;
            min-height: 1.85rem;
            border: 1px solid #d8e0ee;
            border-radius: 999px;
            padding: .25rem .62rem;
            color: #344054;
            background: #ffffff;
            font-size: .88rem;
            font-weight: 650;
        }
        .cy-preview {
            border: 1px solid #d8e0ee;
            border-radius: 8px;
            padding: 1.05rem;
            background: #ffffff;
            box-shadow: 0 14px 34px rgba(24, 40, 72, .08);
        }
        .cy-preview-header {
            display: flex;
            justify-content: space-between;
            gap: .7rem;
            align-items: flex-start;
            border-bottom: 1px solid #edf1f7;
            padding-bottom: .8rem;
            margin-bottom: .85rem;
        }
        .cy-preview-title {
            color: #172033;
            font-size: 1rem;
            font-weight: 850;
            line-height: 1.4;
        }
        .cy-preview-tag {
            flex: 0 0 auto;
            border-radius: 999px;
            padding: .22rem .55rem;
            background: #ecfdf3;
            color: #067647;
            font-size: .78rem;
            font-weight: 800;
        }
        .cy-preview-row {
            display: grid;
            grid-template-columns: 1fr auto;
            gap: .8rem;
            padding: .68rem 0;
            border-bottom: 1px solid #f0f3f8;
            color: #344054;
            font-size: .92rem;
        }
        .cy-preview-row:last-child {
            border-bottom: 0;
        }
        .cy-preview-row strong {
            color: #172033;
        }
        .cy-preview-value {
            color: #2558a8;
            font-weight: 850;
            text-align: right;
        }
        .cy-preview-note {
            margin-top: .8rem;
            border-radius: 8px;
            background: #fff8e6;
            color: #7a5200;
            padding: .72rem .82rem;
            font-size: .88rem;
            line-height: 1.5;
            font-weight: 650;
        }
        .cy-feature-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: .9rem;
            margin: 1.55rem 0 1.25rem;
        }
        .cy-feature {
            border: 1px solid var(--cy-line);
            border-radius: 8px;
            padding: 1.05rem;
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
        .cy-result-hero {
            border: 1px solid #d8e0ee;
            border-radius: 8px;
            padding: 1.15rem 1.2rem;
            background: #ffffff;
            box-shadow: 0 14px 34px rgba(24, 40, 72, .07);
            margin: .7rem 0 1.15rem;
        }
        .cy-result-kicker {
            color: #2558a8;
            font-size: .88rem;
            font-weight: 800;
            margin-bottom: .45rem;
        }
        .cy-result-hero h2 {
            color: #172033;
            font-size: 2rem;
            line-height: 1.22;
            letter-spacing: 0;
            margin: 0 0 .55rem;
        }
        .cy-result-hero p {
            color: #475467;
            font-size: 1rem;
            line-height: 1.6;
            margin: 0;
        }
        .cy-status-row {
            display: flex;
            flex-wrap: wrap;
            gap: .45rem;
            margin-top: .9rem;
        }
        .cy-status-chip {
            display: inline-flex;
            align-items: center;
            min-height: 1.85rem;
            padding: .26rem .64rem;
            border-radius: 999px;
            border: 1px solid #d8e0ee;
            color: #344054;
            background: #ffffff;
            font-size: .86rem;
            font-weight: 750;
        }
        .cy-status-chip.good {
            border-color: #b7e4c7;
            background: #ecfdf3;
            color: #067647;
        }
        .cy-status-chip.warn {
            border-color: #f5d58a;
            background: #fff8e6;
            color: #7a5200;
        }
        .cy-next-actions {
            border: 1px solid #e7edf6;
            border-radius: 8px;
            padding: 1rem 1.05rem;
            background: #fbfcff;
            margin: 0 0 1.2rem;
        }
        .cy-next-actions strong {
            display: block;
            color: #172033;
            font-size: 1.05rem;
            margin-bottom: .55rem;
        }
        .cy-next-actions ol {
            margin: 0;
            padding-left: 1.2rem;
            color: #344054;
            line-height: 1.65;
        }
        .cy-result-card-title {
            min-height: 2.5rem;
        }
        .cy-rank-card {
            display: flex;
            flex-direction: column;
            min-height: 17.2rem;
            border: 1px solid var(--cy-line);
            border-radius: 8px;
            padding: 1.05rem;
            background: var(--cy-surface);
            box-shadow: var(--cy-shadow-soft);
        }
        .cy-rank-meta {
            color: var(--cy-muted);
            font-size: .9rem;
            font-weight: 750;
            margin-bottom: .65rem;
        }
        .cy-rank-card h4 {
            min-height: 2.5rem;
            margin: 0 0 .65rem;
            color: var(--cy-text);
            font-size: 1.25rem;
            line-height: 1.35;
        }
        .cy-rank-score {
            margin: .75rem 0 .45rem;
            color: var(--cy-text);
            font-weight: 850;
        }
        .cy-rank-reason {
            min-height: 3.2rem;
            color: var(--cy-subtext);
            line-height: 1.55;
            margin: .2rem 0 .75rem;
        }
        .cy-rank-details {
            margin-top: auto;
            border: 1px solid var(--cy-line);
            border-radius: 8px;
            background: var(--cy-surface-soft);
            color: var(--cy-text-soft);
            overflow: hidden;
        }
        .cy-rank-details summary {
            cursor: pointer;
            list-style: none;
            padding: .78rem .9rem;
            font-weight: 800;
        }
        .cy-rank-details summary::-webkit-details-marker {
            display: none;
        }
        .cy-rank-details summary::before {
            content: "›";
            display: inline-block;
            margin-right: .55rem;
            color: var(--cy-blue);
            font-weight: 900;
        }
        .cy-rank-details[open] summary::before {
            transform: rotate(90deg);
        }
        .cy-rank-detail-body {
            border-top: 1px solid var(--cy-line);
            padding: .78rem .9rem .88rem;
            color: var(--cy-subtext);
            line-height: 1.6;
        }
        .cy-rank-detail-body ul {
            margin: 0;
            padding-left: 1.05rem;
        }
        .cy-badge {
            display: inline-flex;
            align-items: center;
            min-height: 1.65rem;
            border-radius: 999px;
            padding: .18rem .52rem;
            background: #eef4ff;
            color: #2558a8;
            font-size: .78rem;
            font-weight: 800;
            margin-right: .25rem;
        }
        .cy-muted {
            color: #667085;
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
        div.stButton > button[kind="primary"] {
            border-color: #2558a8;
            background: #2558a8;
            color: #ffffff;
            box-shadow: 0 10px 22px rgba(37, 88, 168, .16);
        }
        div.stButton > button[kind="primary"]:hover {
            border-color: #1f4b91;
            background: #1f4b91;
            color: #ffffff;
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
        .cy-source-list {
            display: flex;
            flex-wrap: wrap;
            gap: .45rem;
            padding-top: .15rem;
        }
        .cy-source-chip {
            display: inline-flex;
            align-items: center;
            max-width: 100%;
            border: 1px solid #d8e0ee;
            border-radius: 999px;
            padding: .28rem .62rem;
            background: #ffffff;
            color: #475467;
            font-size: .82rem;
            line-height: 1.35;
            word-break: keep-all;
        }
        .cy-validation-summary {
            margin-top: .75rem;
            border: 1px solid #f0c7c7;
            border-radius: 8px;
            background: #fff5f5;
            color: #9f2f2f;
            padding: .78rem .9rem;
            line-height: 1.5;
        }
        .cy-validation-summary strong {
            display: block;
            margin-bottom: .18rem;
            color: #8f2929;
            font-weight: 800;
        }
        .cy-validation-summary span {
            color: #b04444;
            font-size: .93rem;
        }
        .cy-theme-toggle {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: .25rem;
            border: 1px solid var(--cy-line);
            border-radius: 8px;
            padding: .22rem;
            background: var(--cy-surface-soft);
        }
        .cy-theme-option {
            display: block;
            text-align: center;
            border-radius: 6px;
            padding: .42rem .5rem;
            color: var(--cy-text-soft);
            text-decoration: none;
            font-weight: 750;
            line-height: 1.2;
        }
        .cy-theme-option:hover {
            background: var(--cy-blue-soft);
            color: var(--cy-blue-strong);
            text-decoration: none;
        }
        .cy-theme-option.active {
            background: var(--cy-blue);
            color: var(--cy-on-blue);
            box-shadow: var(--cy-shadow-blue);
        }
        @media (max-width: 760px) {
            .cy-home-grid {
                grid-template-columns: 1fr;
                gap: 1.15rem;
            }
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
    st.markdown(
        """
        <div class="cy-hero-text">
        <div class="cy-brand">
          <span class="cy-brand-logo-slot" aria-label="로고 자리"></span>
          <h1>청약 랭그래프 시스템</h1>
        </div>
        <p>내 조건을 입력하면 가능한 공급 유형과 추가 확인이 필요한 항목을 한 화면에서 확인할 수 있어요.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="cy-hero-divider"></div>', unsafe_allow_html=True)


def render_home_screen() -> None:
    st.markdown(
        """
        <section class="cy-home">
          <div class="cy-home-grid">
            <div>
              <div class="cy-kicker">3분 청약 진단</div>
              <h2>내게 유리한 청약 유형을<br>먼저 확인해보세요</h2>
              <p>
                통장, 무주택, 혼인, 자녀, 소득 조건을 바탕으로
                지금 검토할 공급유형과 추가 확인 항목을 결과지처럼 정리해드려요.
              </p>
              <div class="cy-home-proof">
                <span>추천 Top 3</span>
                <span>가점 근거</span>
                <span>공고문 분석</span>
                <span>자금 부담 확인</span>
              </div>
            </div>
            <div class="cy-preview">
              <div class="cy-preview-header">
                <div class="cy-preview-title">진단 결과 미리보기</div>
                <div class="cy-preview-tag">예시</div>
              </div>
              <div class="cy-preview-row">
                <span>1순위 추천</span>
                <strong class="cy-preview-value">신혼부부 특공</strong>
              </div>
              <div class="cy-preview-row">
                <span>경쟁력</span>
                <strong class="cy-preview-value">75% · 높음</strong>
              </div>
              <div class="cy-preview-row">
                <span>추가 확인</span>
                <strong class="cy-preview-value">자금 계획</strong>
              </div>
              <div class="cy-preview-note">
                결과에서는 추천 이유, 점수 구성, 공고 기준 다음 행동을 함께 확인할 수 있어요.
              </div>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if st.button("내 청약 가능성 확인하기", type="primary", use_container_width=False):
        st.switch_page(DIAGNOSIS_PAGE)

    st.markdown(
        """
        <section class="cy-home">
          <div class="cy-feature-row">
            <div class="cy-feature">
              <strong>추천 공급유형 Top 3</strong>
              <span>내 조건에서 먼저 검토할 공급유형과 추천 순위를 확인합니다.</span>
            </div>
            <div class="cy-feature">
              <strong>가점과 자격 근거</strong>
              <span>왜 해당 유형이 유리한지 점수와 확인 항목을 함께 보여줍니다.</span>
            </div>
            <div class="cy-feature">
              <strong>공고 기준 상세 분석</strong>
              <span>공고문을 입력하면 내 조건 기준으로 자금 부담과 다음 행동을 정리합니다.</span>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(active_page: str) -> None:
    with st.sidebar:
        st.markdown("### 청약 랭그래프 시스템")
        render_theme_selector()
        st.divider()
        st.caption("모드 전환")
        _sidebar_page_link(HOME_PAGE, "처음 화면", active=active_page == "home")
        _sidebar_page_link(DIAGNOSIS_PAGE, "자가진단", active=active_page == "diagnosis")
        _sidebar_page_link(CHATBOT_PAGE, "FAQ 챗봇", active=active_page == "chatbot")
        st.divider()
        render_api_connection_status()


def render_theme_selector() -> None:
    """발표 중 빠르게 확인할 수 있는 서비스 자체 테마 선택 컨트롤."""
    current_mode = _current_theme_mode()
    st.caption("화면 테마")
    light_col, dark_col = st.columns(2, gap="small")
    with light_col:
        if st.button(
            "라이트",
            key="theme_light_button",
            type="primary" if current_mode == "라이트" else "secondary",
            use_container_width=True,
        ):
            _set_theme_mode("라이트")
            st.rerun()
    with dark_col:
        if st.button(
            "다크",
            key="theme_dark_button",
            type="primary" if current_mode == "다크" else "secondary",
            use_container_width=True,
        ):
            _set_theme_mode("다크")
            st.rerun()


def _set_theme_mode(mode: str) -> None:
    """테마 선택 버튼에서 호출하는 단일 진입점."""
    if mode not in THEME_OPTIONS:
        mode = "라이트"
    st.session_state["theme_mode"] = mode
    _theme_store()["mode"] = mode
    st.query_params["theme"] = mode


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
    report = response.get("report") if isinstance(response.get("report"), dict) else {}
    supply_rank = response.get("supply_rank") or report.get("supply_rank")
    if not isinstance(supply_rank, list):
        return []
    return [item for item in supply_rank[:limit] if isinstance(item, dict)]


def render_result(response: dict) -> None:
    supply_rank = _top_supply_rank(response)
    report = response.get("report") if isinstance(response.get("report"), dict) else {}
    node5 = response.get("node5") if isinstance(response.get("node5"), dict) else {}
    recommended = response.get("recommended_supply") or report.get("recommended_supply")
    if not recommended and supply_rank:
        recommended = supply_rank[0].get("type")

    title = (
        f"{recommended}을 먼저 검토하세요"
        if recommended
        else "청약 가능성과 추가 확인 항목을 확인하세요"
    )
    summary = _result_summary(response, report, node5)
    chips = _result_status_chips(response, report, node5)

    st.markdown(
        f"""
        <section class="cy-result-hero">
          <div class="cy-result-kicker">청약 랭그래프 시스템 진단 결과</div>
          <h2>{escape(title)}</h2>
          <p>{escape(summary)}</p>
          <div class="cy-status-row">
            {''.join(chips)}
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    next_actions = _next_actions(response, report, node5)
    if next_actions:
        items = "".join(f"<li>{escape(action)}</li>" for action in next_actions[:3])
        st.markdown(
            f"""
            <section class="cy-next-actions">
              <strong>지금 확인할 일</strong>
              <ol>{items}</ol>
            </section>
            """,
            unsafe_allow_html=True,
        )

    if supply_rank:
        st.subheader("추천 Top 3")
        rank_columns = st.columns(min(3, len(supply_rank)))
        for index, item in enumerate(supply_rank):
            with rank_columns[index]:
                st.markdown(_rank_card_html(item, index), unsafe_allow_html=True)

    for warning in response.get("warnings", []):
        st.warning(warning)

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


RESULT_SCORE_LABELS = {
    "income": "소득 기준",
    "minor_child_count": "미성년 자녀 수",
    "residence_period_years": "거주기간",
    "bankbook_payments": "청약통장 납입 횟수",
    "marriage_period": "혼인기간",
    "homeless_period_years": "무주택 기간",
    "bankbook_joined_months": "청약통장 가입기간",
    "homeless_score": "무주택기간",
    "dependent_family_score": "부양가족",
    "subscription_score": "청약통장 가입기간",
    "spouse_subscription_score": "배우자 청약통장",
}


def _render_score_breakdown_in_card(item: dict[str, Any]) -> None:
    breakdown = item.get("score_breakdown") or {}
    missing_items = item.get("missing_items") or []
    if breakdown:
        with st.expander("점수 근거"):
            for key, value in breakdown.items():
                label = RESULT_SCORE_LABELS.get(key, key)
                st.markdown(f"- {label}: {value}점")
    if missing_items:
        with st.expander("조건 미달 가능 항목"):
            for missing in missing_items:
                st.markdown(f"- {missing}")


def _rank_card_html(item: dict[str, Any], index: int) -> str:
    """추천 Top3 카드를 라이트/다크에서 같은 높이로 렌더링한다."""
    rank = escape(str(item.get("rank", index + 1)))
    supply_type = escape(str(item.get("type", "공급 유형")))
    method = escape(str(item.get("method") or "기준 확인"))
    competitiveness = item.get("competitiveness")
    badges = f"<span class='cy-badge'>{method}</span>"
    if competitiveness:
        badges += f"<span class='cy-badge'>{escape(str(competitiveness))}</span>"

    score = item.get("score")
    max_score = item.get("max_score")
    if score is None or max_score is None:
        score_text = "별도 점수 산정 없음"
    else:
        ratio = item.get("ratio")
        score_text = f"{escape(str(score))}/{escape(str(max_score))}점" + (
            f" · {escape(str(ratio))}" if ratio else ""
        )

    reason = escape(str(item.get("reason") or "공급유형별 세부 기준을 확인해 주세요."))
    details = _rank_detail_html(item)
    return f"""
    <article class="cy-rank-card">
      <div class="cy-rank-meta">{rank}순위</div>
      <h4>{supply_type}</h4>
      <div>{badges}</div>
      <div class="cy-rank-score">{score_text}</div>
      <div class="cy-rank-reason">{reason}</div>
      {details}
    </article>
    """


def _rank_detail_html(item: dict[str, Any]) -> str:
    breakdown = item.get("score_breakdown") or {}
    missing_items = item.get("missing_items") or []
    detail_items: list[str] = []

    for key, value in breakdown.items():
        label = RESULT_SCORE_LABELS.get(key, key)
        detail_items.append(f"<li>{escape(str(label))}: {escape(str(value))}점</li>")
    for missing in missing_items:
        detail_items.append(f"<li>{escape(str(missing))}</li>")

    if not detail_items:
        return '<div class="cy-rank-details"><div class="cy-rank-detail-body">세부 근거 없음</div></div>'

    summary = "점수 근거" if breakdown else "조건 미달 가능 항목"
    if breakdown and missing_items:
        summary = "점수 근거와 미달 가능 항목"
    return f"""
    <details class="cy-rank-details">
      <summary>{summary}</summary>
      <div class="cy-rank-detail-body"><ul>{''.join(detail_items)}</ul></div>
    </details>
    """


def _result_summary(response: dict[str, Any], report: dict[str, Any], node5: dict[str, Any]) -> str:
    risk_level, risk_description = _finance_risk(report, node5)
    if risk_level:
        if risk_level == "높음":
            return "자격과 추천 유형을 확인했습니다. 다만 자금 부담이 커서 대출 가능 여부와 추가 자금 계획을 먼저 점검해야 합니다."
        return f"추천 유형과 주요 조건을 확인했습니다. 자금 부담은 {risk_level} 수준으로 정리됩니다."
    guide_message = response.get("guide_message")
    if isinstance(guide_message, str) and guide_message.strip():
        return guide_message.strip()
    return "입력한 조건을 바탕으로 유리한 공급유형과 다음 확인 항목을 정리했습니다."


def _result_status_chips(response: dict[str, Any], report: dict[str, Any], node5: dict[str, Any]) -> list[str]:
    chips = ["<span class='cy-status-chip good'>추천 유형 확인</span>"]
    if response.get("announcement") or report.get("announcement"):
        chips.append("<span class='cy-status-chip good'>공고 기준 반영</span>")
    else:
        chips.append("<span class='cy-status-chip'>기본 조건 기준</span>")
    risk_level, _ = _finance_risk(report, node5)
    if risk_level:
        chip_class = "warn" if risk_level == "높음" else "good"
        chips.append(f"<span class='cy-status-chip {chip_class}'>자금 부담 {risk_level}</span>")
    if response.get("result_status"):
        chips.append("<span class='cy-status-chip'>진단 완료</span>")
    return chips


def _next_actions(response: dict[str, Any], report: dict[str, Any], node5: dict[str, Any]) -> list[str]:
    actions = [str(item) for item in response.get("next_actions", []) if item]
    recommended = response.get("recommended_supply") or report.get("recommended_supply")
    if recommended:
        actions.append(f"{recommended}의 세부 자격과 우선공급 기준을 공고문에서 확인하세요.")
    if response.get("announcement") or report.get("announcement"):
        actions.append("공고문 기준 공급 세대수와 해당지역 우선공급 기준을 확인하세요.")
    risk_level, _ = _finance_risk(report, node5)
    if risk_level == "높음":
        actions.append("중도금 대출 가능 여부와 부족 자금 조달 계획을 먼저 점검하세요.")
    if not actions:
        actions.append("청약통장 가입기간, 납입 횟수, 지역별 예치금 충족 여부를 확인하세요.")
    deduped: list[str] = []
    for action in actions:
        if action not in deduped:
            deduped.append(action)
    return deduped


def _finance_risk(report: dict[str, Any], node5: dict[str, Any]) -> tuple[str | None, str | None]:
    finance = report.get("finance") if isinstance(report.get("finance"), dict) else {}
    risk = node5.get("risk_result") if isinstance(node5.get("risk_result"), dict) else {}
    risk_level = finance.get("risk_level") or risk.get("risk_level")
    risk_description = finance.get("risk_description") or risk.get("description")
    return risk_level, risk_description
