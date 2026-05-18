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
        .stTabs [data-baseweb="tab"] {
            font-family: 'Calibri', sans-serif !important;
        }
        /* Hide sidebar and the toggle arrow completely */
        [data-testid="stSidebar"] {
            display: none;
        }
        [data-testid="collapsedControl"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

# ── App header with logo ─────────────────────────────────────────────────────
col1, col2 = st.columns([1, 8])
with col1:
    st.image("https://raw.githubusercontent.com/Ryan-Greene/media-contacts-app/main/logo.png", width=80)
with col2:
    st.title("Boulder")
    st.caption("C&P Communications · Media Database")

st.markdown("---")

# ── Top tab navigation ───────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Browse Contacts",
    "📋 Build a List",
    "➕ Add Contact",
    "⬆️ Import Contacts",
    "✏️ Manage Contacts",
])

with tab1:
    from pages.browse import show
    show()

with tab2:
    from pages.build_list import show
    show()

with tab3:
    from pages.add_contact import show
    show()

with tab4:
    from pages.import_contacts import show
    show()

with tab5:
    from pages.manage import show
    show()
