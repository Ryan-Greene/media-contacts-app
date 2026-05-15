import streamlit as st
from utils.airtable import get_all_contacts
import pandas as pd

def show():
    st.title("🔍 Browse Contacts")
    st.caption("Search and filter your full media database.")

    with st.spinner("Loading contacts..."):
        contacts = get_all_contacts()

    if not contacts:
        st.warning("No contacts found. Import your media list first.")
        return

    df = pd.DataFrame(contacts)

    # ── Filters ──────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns([3,2,2,2])

    with col1:
        search = st.text_input("🔎 Search", placeholder="Name, outlet, title, email...")

    with col2:
        media_types = ["All"] + sorted(df["Media Type"].dropna().unique().tolist())
        media_filter = st.selectbox("Media Type", media_types)

    with col3:
        all_clients = set()
        for c in contacts:
            for tag in (c.get("Client(s)") or "").split(","):
                t = tag.strip()
                if t: all_clients.add(t)
        client_filter = st.selectbox("Client", ["All"] + sorted(all_clients))

    with col4:
        market_types = ["All"] + sorted(df["Market Type"].dropna().unique().tolist())
        market_filter = st.selectbox("Market Type", market_types)

    # ── Apply filters ────────────────────────────────────────────────────────
    filtered = contacts

    if search:
        s = search.lower()
        filtered = [c for c in filtered if any(
            s in str(c.get(f, "")).lower()
            for f in ["Outlet","Contact First","Contact Last","Title","Email"]
        )]

    if media_filter != "All":
        filtered = [c for c in filtered if c.get("Media Type") == media_filter]

    if client_filter != "All":
        filtered = [c for c in filtered
                    if client_filter in [t.strip() for t in (c.get("Client(s)") or "").split(",")]]

    if market_filter != "All":
        filtered = [c for c in filtered if c.get("Market Type") == market_filter]

    st.markdown(f"**{len(filtered)}** contacts found")
    st.markdown("---")

    # ── Display ──────────────────────────────────────────────────────────────
    DISPLAY_COLS = ["Outlet","Contact First","Contact Last","Title","Email",
                    "Phone","Market Type","Client(s)","Media Type"]

    if filtered:
        rows = []
        for c in sorted(filtered, key=lambda x: (x.get("Outlet") or "").lower()):
            rows.append({col: c.get(col, "") or "" for col in DISPLAY_COLS})
        df_show = pd.DataFrame(rows)
        st.dataframe(df_show, use_container_width=True, hide_index=True,
                     column_config={
                         "Email": st.column_config.LinkColumn("Email", display_text="✉️ Email"),
                     })
    else:
        st.info("No contacts match your filters.")
