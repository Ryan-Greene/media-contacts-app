import streamlit as st
import pandas as pd
import openpyxl
import io
from utils.airtable import create_contacts, get_all_contacts

MEDIA_TYPE_MAP = {
    "print/online": "Print & Online", "print & online": "Print & Online",
    "broadcast":    "Broadcast (TV)", "broadcast (tv)": "Broadcast (TV)",
    "radio":        "Radio",
    "newsletter":   "Newsletter",
    "podcast":      "Podcast",
    "trade":        "Trade Media",    "trade media": "Trade Media",
}

STANDARD_COLS = ["Outlet","Contact First","Contact Last","Title","Email",
                 "Phone","Market Type","Market","Client(s)","Media Type",
                 "Trade Sub","Notes","Website"]

def show():
    st.title("⬆️ Import Contacts")
    st.caption("Upload a client's Excel media list and push new contacts to the database.")

    uploaded = st.file_uploader("Drop an Excel file here", type=["xlsx","xls"])

    if not uploaded:
        st.info("Upload an .xlsx file to get started.")
        return

    # ── Read file ─────────────────────────────────────────────────────────────
    wb = openpyxl.load_workbook(io.BytesIO(uploaded.read()), read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not rows:
        st.error("File appears to be empty.")
        return

    raw_headers = [str(v).strip() if v else "" for v in rows[0]]
    st.success(f"File read — {len(rows)-1} rows, {len(raw_headers)} columns.")

    # ── Column mapping ────────────────────────────────────────────────────────
    st.subheader("Map Columns")
    st.caption("Match your file's columns to the standard fields. Skip any that don't apply.")

    col_map = {}
    options = ["(skip)"] + raw_headers

    mapping_cols = st.columns(3)
    fields_to_map = ["Outlet","Contact First","Contact Last","Title","Email",
                     "Phone","Market Type","Market","Media Type","Client(s)","Notes","Website"]

    # Auto-detect obvious matches
    def auto_match(field):
        fl = field.lower().replace(" ","").replace("(","").replace(")","")
        for h in raw_headers:
            hl = h.lower().replace(" ","").replace("(","").replace(")","")
            if fl == hl or fl in hl or hl in fl:
                return h
        return "(skip)"

    for i, field in enumerate(fields_to_map):
        with mapping_cols[i % 3]:
            default = auto_match(field)
            idx = options.index(default) if default in options else 0
            col_map[field] = st.selectbox(f"**{field}**", options, index=idx, key=f"map_{field}")

    # ── Client tag ────────────────────────────────────────────────────────────
    st.subheader("Client Tag")
    client_tag = st.text_input("Tag all imported contacts with this client",
                                placeholder="e.g. SO, FAPIA, LifeLink")

    # ── Preview ───────────────────────────────────────────────────────────────
    st.subheader("Preview")

    def parse_rows():
        contacts = []
        for row in rows[1:]:
            if not any(row): continue
            def g(field):
                col = col_map.get(field,"(skip)")
                if col == "(skip)": return ""
                idx = raw_headers.index(col) if col in raw_headers else -1
                if idx < 0 or idx >= len(row): return ""
                v = row[idx]
                return str(v).strip() if v is not None else ""

            email = g("Email")
            if not email or email.lower() in ("n/a","contact link","none",""): continue

            mt_raw = g("Media Type").lower()
            media_type = MEDIA_TYPE_MAP.get(mt_raw, "Print & Online")

            clients = g("Client(s)")
            if client_tag:
                clients = client_tag if not clients else f"{clients}, {client_tag}"

            contacts.append({
                "Outlet":        g("Outlet"),
                "Contact First": g("Contact First"),
                "Contact Last":  g("Contact Last"),
                "Title":         g("Title"),
                "Email":         email,
                "Phone":         g("Phone"),
                "Market Type":   g("Market Type"),
                "Market":        g("Market"),
                "Media Type":    media_type,
                "Client(s)":     clients,
                "Notes":         g("Notes"),
                "Website":       g("Website"),
            })
        return contacts

    preview_contacts = parse_rows()
    st.markdown(f"**{len(preview_contacts)} contacts** ready to import.")

    if preview_contacts:
        preview_df = pd.DataFrame(preview_contacts[:20])
        st.dataframe(preview_df[["Outlet","Contact First","Contact Last",
                                  "Email","Media Type","Client(s)"]],
                     use_container_width=True, hide_index=True)
        if len(preview_contacts) > 20:
            st.caption(f"Showing first 20 of {len(preview_contacts)}")

    # ── Deduplicate check ─────────────────────────────────────────────────────
    st.subheader("Duplicate Check")
    check_dupes = st.checkbox("Skip contacts already in the database (matched by email)", value=True)

    # ── Import button ─────────────────────────────────────────────────────────
    st.markdown("---")
    if st.button("⬆️ Import to Airtable", type="primary", disabled=not preview_contacts):
        to_import = preview_contacts

        if check_dupes:
            with st.spinner("Checking for duplicates..."):
                existing = get_all_contacts()
                existing_emails = {(c.get("Email") or "").lower() for c in existing}
                to_import = [c for c in to_import
                             if c["Email"].lower() not in existing_emails]
            st.info(f"{len(preview_contacts) - len(to_import)} duplicates skipped. "
                    f"Importing {len(to_import)} new contacts.")

        if to_import:
            with st.spinner(f"Importing {len(to_import)} contacts..."):
                success, errors = create_contacts(to_import)
            if success:
                st.success(f"✅ {success} contacts imported successfully!")
                st.cache_data.clear()
            if errors:
                st.error(f"{len(errors)} batches failed.")
                for e in errors[:3]: st.code(e)
        else:
            st.info("No new contacts to import after duplicate check.")
