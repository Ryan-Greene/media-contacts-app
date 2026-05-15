import streamlit as st
from utils.airtable import get_all_contacts
from utils.excel import build_excel
import pandas as pd
from datetime import date

def show():
    st.title("📋 Build a List")
    st.caption("Filter contacts and export a formatted Excel media list.")

    with st.spinner("Loading contacts..."):
        contacts = get_all_contacts()

    if not contacts:
        st.warning("No contacts found.")
        return

    # ── Filters ──────────────────────────────────────────────────────────────
    st.subheader("Filter Contacts")
    col1, col2 = st.columns(2)

    with col1:
        # Client filter
        all_clients = set()
        for c in contacts:
            for tag in (c.get("Client(s)") or "").split(","):
                t = tag.strip()
                if t: all_clients.add(t)
        selected_clients = st.multiselect("Client(s)", sorted(all_clients))

        # Media type filter
        all_media = sorted(set(c.get("Media Type","") for c in contacts if c.get("Media Type")))
        selected_media = st.multiselect("Media Type", all_media)

    with col2:
        # Market type filter
        all_market_types = sorted(set(c.get("Market Type","") for c in contacts if c.get("Market Type")))
        selected_market_types = st.multiselect("Market Type", all_market_types)

        # Search
        search = st.text_input("🔎 Keyword search", placeholder="Outlet, beat, title...")

    # ── Apply filters ────────────────────────────────────────────────────────
    filtered = contacts

    if selected_clients:
        filtered = [c for c in filtered if any(
            tag in [t.strip() for t in (c.get("Client(s)") or "").split(",")]
            for tag in selected_clients
        )]

    if selected_media:
        filtered = [c for c in filtered if c.get("Media Type") in selected_media]

    if selected_market_types:
        filtered = [c for c in filtered if c.get("Market Type") in selected_market_types]

    if search:
        s = search.lower()
        filtered = [c for c in filtered if any(
            s in str(c.get(f,"")).lower()
            for f in ["Outlet","Contact First","Contact Last","Title","Notes"]
        )]

    st.markdown("---")
    st.markdown(f"**{len(filtered)} contacts** will be included in this list.")

    # ── Preview ──────────────────────────────────────────────────────────────
    if filtered:
        DISPLAY_COLS = ["Outlet","Contact First","Contact Last","Title",
                        "Email","Media Type","Market Type","Client(s)"]
        rows = [{col: c.get(col,"") or "" for col in DISPLAY_COLS}
                for c in sorted(filtered, key=lambda x: (x.get("Outlet") or "").lower())]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── Export ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Export")

    list_name = st.text_input("List name (for filename)", 
                               value=f"Media_List_{date.today().strftime('%B_%Y')}")

    if filtered:
        excel_bytes = build_excel(filtered, list_name)
        st.download_button(
            label="⬇️ Download Excel",
            data=excel_bytes,
            file_name=f"{list_name.replace(' ','_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("Adjust your filters to select contacts for export.")
