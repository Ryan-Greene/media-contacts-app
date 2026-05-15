import streamlit as st
from utils.airtable import create_contacts, get_all_contacts

MEDIA_TYPES  = ["Print & Online", "Broadcast (TV)", "Radio", "Newsletter", "Podcast", "Trade Media"]
MARKET_TYPES = ["Local", "Regional", "Statewide", "National", "International"]
TRADE_SUBS   = ["", "Trade - Architecture", "Trade - Classical Music", "Trade - Disability",
                "Trade - Education", "Trade - Health", "Trade - Insurance",
                "Trade - Military", "Trade - Philanthropy", "Trade - General"]

def show():
    st.title("➕ Add Contact")
    st.caption("Add a single contact directly to the database.")

    with st.form("add_contact_form"):
        st.subheader("Outlet")
        col1, col2 = st.columns(2)
        with col1:
            outlet     = st.text_input("Outlet *", placeholder="e.g. Orlando Sentinel")
            media_type = st.selectbox("Media Type *", MEDIA_TYPES)
            trade_sub  = st.selectbox("Trade Sub (if Trade Media)", TRADE_SUBS)
        with col2:
            market_type = st.selectbox("Market Type", MARKET_TYPES)
            market      = st.text_input("Market", placeholder="e.g. Orlando")
            website     = st.text_input("Website", placeholder="e.g. orlandosentinel.com")

        st.subheader("Contact")
        col3, col4 = st.columns(2)
        with col3:
            first = st.text_input("First Name", placeholder="e.g. Sarah")
            email = st.text_input("Email *", placeholder="e.g. sarah@outlet.com")
            phone = st.text_input("Phone", placeholder="e.g. 407-555-1234")
        with col4:
            last    = st.text_input("Last Name", placeholder="e.g. Johnson")
            title   = st.text_input("Title", placeholder="e.g. Reporter")
            clients = st.text_input("Client(s)", placeholder="e.g. SO, FAPIA")

        notes = st.text_area("Notes", placeholder="Beat, relationship notes, etc.", height=80)

        st.markdown("---")
        submitted = st.form_submit_button("➕ Add to Database", type="primary")

    if submitted:
        # Validation
        if not outlet:
            st.error("Outlet is required.")
            return
        if not email:
            st.error("Email is required.")
            return

        # Duplicate check
        with st.spinner("Checking for duplicates..."):
            existing = get_all_contacts()
            existing_emails = {(c.get("Email") or "").lower() for c in existing}

        if email.lower() in existing_emails:
            st.warning(f"A contact with email **{email}** already exists in the database.")
            return

        contact = {
            "Outlet":        outlet,
            "Contact First": first,
            "Contact Last":  last,
            "Title":         title,
            "Email":         email,
            "Phone":         phone,
            "Market Type":   market_type,
            "Market":        market,
            "Media Type":    media_type,
            "Trade Sub":     trade_sub if media_type == "Trade Media" else "",
            "Client(s)":     clients,
            "Notes":         notes,
            "Website":       website,
        }

        with st.spinner("Adding contact..."):
            success, errors = create_contacts([contact])

        if success:
            st.success(f"✅ {first} {last} from {outlet} added successfully!")
            st.cache_data.clear()
        else:
            st.error(f"Something went wrong: {errors}")
