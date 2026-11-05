"""
SIP Pause Guide — Streamlit entry point.

Sidebar router: Guide | Quality.
Footer on every page: "Prototype for research. Not investment advice."
"""
import streamlit as st

from lib.content import FOOTER
from views import guide, quality

st.set_page_config(
    page_title="SIP Pause Guide",
    page_icon="\U0001f4ca",
    layout="centered",
)

# Hard Rule 8: Minimum font 14px, colour-blind-safe styling, usable at 375px width
st.markdown(
    """
    <style>
    html, body, [class*="css"], [class*="st-"] {
        font-size: 15px !important;
    }
    .stApp {
        max-width: 100%;
        margin: 0 auto;
    }
    @media (max-width: 375px) {
        .block-container {
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
        }
        button {
            min-height: 44px !important;
        }
    }
    button {
        cursor: pointer !important;
        transition: all 0.15s ease-in-out !important;
    }
    button[kind="secondary"], button[data-testid="stBaseButton-secondary"] {
        border-radius: 8px !important;
        border: 1px solid #D0D5DD !important;
        background-color: #FFFFFF !important;
        color: #344054 !important;
        font-weight: 500 !important;
    }
    button[kind="secondary"]:hover, button[data-testid="stBaseButton-secondary"]:hover {
        border-color: #00D09C !important;
        color: #008765 !important;
        background-color: #F4FBF8 !important;
    }
    button[kind="secondary"]:active, button[data-testid="stBaseButton-secondary"]:active {
        background-color: #E6F7F2 !important;
        border-color: #00D09C !important;
    }
    button:focus-visible, [role="button"]:focus-visible, input:focus-visible, textarea:focus-visible {
        outline: 2px solid #00D09C !important;
        outline-offset: 2px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar router (spec §4)
page = st.sidebar.radio("Navigate", ["Guide", "Quality"], label_visibility="collapsed")

if page == "Guide":
    guide.render()
else:
    quality.render()

# Footer on every page (spec §4)
st.divider()
st.caption(FOOTER)
