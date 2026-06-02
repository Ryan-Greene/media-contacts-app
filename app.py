import streamlit as st

st.set_page_config(
    page_title="Boulder",
    page_icon="🪨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
    <style>
        * {
            font-family: 'Calibri', sans-serif !important;
        }
        [data-testid="collapsedControl"] {
            display: none;
        }
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #1a1a2e;
        }
        [data-testid="stSidebar"] .stRadio label {
            font-size: 15px;
            padding: 8px 0;
            color: #ffffff;
        }
        /* Clean up main area top padding */
        .block-container {
            padding-top: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

# ── Sidebar navigation ───────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://raw.githubusercontent.com/Ryan-Greene/media-contacts-app/main/c%26pboulder.png", width=120)
    st.markdown("## Boulder")
    st.caption("C&P Communications")
    st.markdown("---")
    page = st.radio("", [
        "💬 Boulder Bot",
        "🔍 Browse Contacts",
        "📋 Build a List",
        "➕ Add Contact",
        "⬆️ Import Contacts",
        "✏️ Manage Contacts",
    ], label_visibility="collapsed")
    st.markdown("---")
    st.caption("Media Database · C&P")

# ── Route to page ────────────────────────────────────────────────────────────
if page == "💬 Boulder Bot":
    from pages.chat import show
    show()
elif page == "🔍 Browse Contacts":
    from pages.browse import show
    show()
elif page == "📋 Build a List":
    from pages.build_list import show
    show()
elif page == "➕ Add Contact":
    from pages.add_contact import show
    show()
elif page == "⬆️ Import Contacts":
    from pages.import_contacts import show
    show()
elif page == "✏️ Manage Contacts":
    from pages.manage import show
    show()
