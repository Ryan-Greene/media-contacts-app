import streamlit as st

st.set_page_config(
    page_title="C&P Media Contacts",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Shared Airtable client ───────────────────────────────────────────────────
from utils.airtable import get_all_contacts

# ── Sidebar nav ─────────────────────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/fluency/96/news.png", width=60)
st.sidebar.title("C&P Media Contacts")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["🔍 Browse Contacts", "📋 Build a List", "⬆️ Import Contacts", "✏️ Manage Contacts"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.caption("C&P Communications · Media Database")

# ── Route to page ────────────────────────────────────────────────────────────
if page == "🔍 Browse Contacts":
    from pages.browse import show
    show()
elif page == "📋 Build a List":
    from pages.build_list import show
    show()
elif page == "⬆️ Import Contacts":
    from pages.import_contacts import show
    show()
elif page == "✏️ Manage Contacts":
    from pages.manage import show
    show()
