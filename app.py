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

# Sidebar router (spec §4)
page = st.sidebar.radio("Navigate", ["Guide", "Quality"], label_visibility="collapsed")

if page == "Guide":
    guide.render()
else:
    quality.render()

# Footer on every page (spec §4)
st.divider()
st.caption(FOOTER)

