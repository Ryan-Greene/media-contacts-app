import streamlit as st

st.set_page_config(
    page_title="Boulder",
    page_icon="🪨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
    <style>
        * { font-family: 'Calibri', sans-serif !important; }
        [data-testid="collapsedControl"] { display: none; }
        [data-testid="stSidebar"] { display: none; }
        .block-container { padding-top: 1rem; }
    </style>
""", unsafe_allow_html=True)

from pages.chat import show
show()
