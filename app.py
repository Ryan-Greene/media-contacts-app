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

        /* Hide default sidebar toggle */
        [data-testid="collapsedControl"] { display: none; }

        /* Remove default top padding */
        .block-container { padding-top: 1rem; padding-bottom: 0; }

        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #111111;
            min-width: 60px !important;
            max-width: 60px !important;
        }
        [data-testid="stSidebar"] > div {
            padding: 1rem 0.25rem;
        }
        /* Hide sidebar text labels, show only icons */
        [data-testid="stSidebar"] .stRadio > label { display: none; }
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
        }
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
            display: flex !important;
            justify-content: center;
            align-items: center;
            width: 42px;
            height: 42px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 20px;
            background: transparent;
            transition: background 0.2s;
        }
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
            background: #2a2a2a;
        }
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label[data-checked="true"] {
            background: #333333;
        }
        /* Hide radio button circles */
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label span:first-child {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

# ── Slim icon sidebar ─────────────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://raw.githubusercontent.com/Ryan-Greene/media-contacts-app/main/c%26pboulder.png",
        width=44
    )
    st.markdown("<br>", unsafe_allow_html=True)
    page = st.radio("", [
        "💬", "🔍", "📋", "➕", "⬆️", "✏️"
    ], label_visibility="collapsed")
    st.markdown("<br><br><br><br><br><br><br><br>", unsafe_allow_html=True)

# Map icon to page name
PAGE_MAP = {
    "💬": "chat",
    "🔍": "browse",
    "📋": "build_list",
    "➕": "add_contact",
    "⬆️": "import_contacts",
    "✏️": "manage",
}

# Tooltip labels shown at top of main area
PAGE_LABELS = {
    "💬": "",
    "🔍": "Browse Contacts",
    "📋": "Build a List",
    "➕": "Add Contact",
    "⬆️": "Import Contacts",
    "✏️": "Manage Contacts",
}

current = PAGE_MAP.get(page, "chat")
label = PAGE_LABELS.get(page, "")
if label:
    st.caption(label)

# ── Route ─────────────────────────────────────────────────────────────────────
if current == "chat":
    from pages.chat import show
    show()
elif current == "browse":
    from pages.browse import show
    show()
elif current == "build_list":
    from pages.build_list import show
    show()
elif current == "add_contact":
    from pages.add_contact import show
    show()
elif current == "import_contacts":
    from pages.import_contacts import show
    show()
elif current == "manage":
    from pages.manage import show
    show()
