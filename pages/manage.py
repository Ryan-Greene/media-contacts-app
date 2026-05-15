import streamlit as st
from utils.airtable import get_all_contacts, update_contact, delete_contact

MEDIA_TYPES  = ["Print & Online","Broadcast (TV)","Radio","Newsletter","Podcast","Trade Media"]
MARKET_TYPES = ["Local","Regional","Statewide","National","International"]
TRADE_SUBS   = ["","Trade - Architecture","Trade - Classical Music","Trade - Disability",
                "Trade - Education","Trade - Health","Trade - Insurance",
                "Trade - Military","Trade - Philanthropy","Trade - General"]

def show():
    st.title("✏️ Manage Contacts")
    st.caption("Search for a contact to edit or delete.")

    with st.spinner("Loading contacts..."):
        contacts = get_all_contacts()

    if not contacts:
        st.warning("No contacts found.")
        return

    # ── Search ────────────────────────────────────────────────────────────────
    search = st.text_input("🔎 Search by name, outlet, or email")

    if not search:
        st.info("Type a name, outlet, or email to find a contact.")
        return

    s = search.lower()
    results = [c for c in contacts if any(
        s in str(c.get(f,"")).lower()
        for f in ["Outlet","Contact First","Contact Last","Email"]
    )]

    if not results:
        st.warning("No contacts found matching that search.")
        return

    st.markdown(f"**{len(results)} result(s)**")

    # ── List results ─────────────────────────────────────────────────────────
    for c in sorted(results, key=lambda x: (x.get("Outlet") or "").lower()):
        outlet = c.get("Outlet","Unknown outlet")
        name   = f"{c.get('Contact First','')} {c.get('Contact Last','')}".strip()
        label  = f"{outlet} — {name}" if name else outlet

        with st.expander(label):
            with st.form(key=f"form_{c['_id']}"):
                col1, col2 = st.columns(2)
                with col1:
                    outlet_v  = st.text_input("Outlet",        value=c.get("Outlet",""))
                    first_v   = st.text_input("Contact First",  value=c.get("Contact First",""))
                    last_v    = st.text_input("Contact Last",   value=c.get("Contact Last",""))
                    title_v   = st.text_input("Title",          value=c.get("Title",""))
                    email_v   = st.text_input("Email",          value=c.get("Email",""))
                    phone_v   = st.text_input("Phone",          value=c.get("Phone",""))

                with col2:
                    mt_idx    = MEDIA_TYPES.index(c.get("Media Type","Print & Online")) \
                                if c.get("Media Type") in MEDIA_TYPES else 0
                    media_v   = st.selectbox("Media Type", MEDIA_TYPES, index=mt_idx)

                    ts_val    = c.get("Trade Sub","") or ""
                    ts_idx    = TRADE_SUBS.index(ts_val) if ts_val in TRADE_SUBS else 0
                    trade_v   = st.selectbox("Trade Sub", TRADE_SUBS, index=ts_idx)

                    mkt_idx   = MARKET_TYPES.index(c.get("Market Type","Local")) \
                                if c.get("Market Type") in MARKET_TYPES else 0
                    mkttype_v = st.selectbox("Market Type", MARKET_TYPES, index=mkt_idx)
                    market_v  = st.text_input("Market",   value=c.get("Market",""))
                    clients_v = st.text_input("Client(s)", value=c.get("Client(s)",""))
                    website_v = st.text_input("Website",   value=c.get("Website",""))

                notes_v = st.text_area("Notes", value=c.get("Notes",""), height=80)

                btn_col1, btn_col2 = st.columns([1,1])
                with btn_col1:
                    save = st.form_submit_button("💾 Save Changes", type="primary")
                with btn_col2:
                    delete = st.form_submit_button("🗑️ Delete Contact",
                                                    type="secondary",
                                                    help="This cannot be undone")

            if save:
                try:
                    update_contact(c["_id"], {
                        "Outlet": outlet_v, "Contact First": first_v,
                        "Contact Last": last_v, "Title": title_v,
                        "Email": email_v, "Phone": phone_v,
                        "Media Type": media_v, "Trade Sub": trade_v,
                        "Market Type": mkttype_v, "Market": market_v,
                        "Client(s)": clients_v, "Website": website_v,
                        "Notes": notes_v,
                    })
                    st.success("✅ Contact updated!")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Update failed: {e}")

            if delete:
                try:
                    delete_contact(c["_id"])
                    st.success("🗑️ Contact deleted.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Delete failed: {e}")
