import streamlit as st
from utils.airtable import get_all_contacts, create_contacts
from utils.excel import build_excel
import re
import pandas as pd

CLIENTS = ["811", "Beacon College", "EA Orlando", "FAPIA", "LifeLink", "OIC", "SO"]
MEDIA_TYPES = ["Print & Online", "Broadcast (TV)", "Radio", "Newsletter", "Podcast", "Trade Media"]

def find_contacts_by_name(name, contacts):
    name_lower = name.lower().strip()
    name_parts = name_lower.split()
    matched = []
    for c in contacts:
        fn = (c.get("Contact First") or "").lower()
        ln = (c.get("Contact Last") or "").lower()
        full = f"{fn} {ln}".strip()
        if (name_lower == full or
            (len(name_parts) == 2 and name_parts[0] == fn and name_parts[1] == ln) or
            (len(name_parts) == 1 and name_lower == fn) or
            (len(name_parts) == 1 and name_lower == ln)):
            matched.append(c)
    return matched

def find_contacts_by_outlet(outlet_name, contacts):
    o = re.sub(r'^the\s+', '', outlet_name.lower().strip())
    return [c for c in contacts if o in (c.get("Outlet") or "").lower()]

def parse_request(text, contacts):
    text_lower = text.lower().strip()

    # Outlet lookup
    outlet_patterns = [
        r"contact(?:s)? (?:from|at|with|for) (.+?)(?:\?|$)",
        r"anyone (?:from|at) (.+?)(?:\?|$)",
        r"who (?:do we have )?(?:from|at) (.+?)(?:\?|$)",
    ]
    for pattern in outlet_patterns:
        m = re.search(pattern, text_lower)
        if m:
            outlet_name = re.sub(r'^the\s+', '', m.group(1).strip().rstrip("?").strip())
            matched = find_contacts_by_outlet(outlet_name, contacts)
            if not matched:
                return f"I don't see any contacts from **{outlet_name.title()}** in the database.", [], "text"
            return f"Found **{len(matched)} contact(s)** from **{outlet_name.title()}**:", matched, "table"

    # Field lookup
    field_map = {
        "email": "Email", "phone": "Phone", "number": "Phone",
        "title": "Title", "outlet": "Outlet", "website": "Website",
        "market": "Market", "client": "Client(s)",
    }
    field_pattern = r"(?:what is|what's|get|find|show)(?: me)? (.+?)(?:'s|s') (email|phone|number|title|outlet|website|market|client)"
    m = re.search(field_pattern, text_lower)
    if m:
        name_str = m.group(1).strip()
        field = field_map.get(m.group(2).strip())
        matched = find_contacts_by_name(name_str, contacts)
        if not matched:
            return f"I couldn't find anyone named **{name_str.title()}** in the database.", [], "text"
        lines = []
        for c in matched:
            val = c.get(field, "") or "not on file"
            name = f"{c.get('Contact First','')} {c.get('Contact Last','')}".strip() or c.get('Outlet','')
            lines.append(f"**{name}** ({c.get('Outlet','')}) — {field}: **{val}**")
        return "\n\n".join(lines), [], "text"

    poss_pattern = r"(.+?)(?:'s|s') (email|phone|number|title|outlet|website)"
    m = re.search(poss_pattern, text_lower)
    if m:
        name_str = m.group(1).strip()
        field = field_map.get(m.group(2).strip())
        matched = find_contacts_by_name(name_str, contacts)
        if not matched:
            return f"I couldn't find anyone named **{name_str.title()}** in the database.", [], "text"
        lines = []
        for c in matched:
            val = c.get(field, "") or "not on file"
            name = f"{c.get('Contact First','')} {c.get('Contact Last','')}".strip() or c.get('Outlet','')
            lines.append(f"**{name}** ({c.get('Outlet','')}) — {field}: **{val}**")
        return "\n\n".join(lines), [], "text"

    # Find person
    find_patterns = [r"(?:find|look up|search for|tell me about|who is|show me) (.+?)(?:\?|$)"]
    for pattern in find_patterns:
        m = re.search(pattern, text_lower)
        if m:
            name_str = m.group(1).strip().rstrip("?").strip()
            matched = find_contacts_by_name(name_str, contacts)
            if matched:
                return f"Here's what I found for **{name_str.title()}**:", matched, "table"
            outlet_matched = find_contacts_by_outlet(name_str, contacts)
            if outlet_matched:
                return f"Found **{len(outlet_matched)} contact(s)** at **{name_str.title()}**:", outlet_matched, "table"
            return f"I couldn't find **{name_str.title()}** in the database.", [], "text"

    # How many
    if "how many" in text_lower:
        media_map = {"broadcast": "Broadcast (TV)", "tv": "Broadcast (TV)", "radio": "Radio",
                     "print": "Print & Online", "newsletter": "Newsletter",
                     "podcast": "Podcast", "trade": "Trade Media"}
        for kw, mt in media_map.items():
            if kw in text_lower:
                count = sum(1 for c in contacts if c.get("Media Type") == mt)
                return f"There are **{count} {mt} contacts** in the database.", [], "text"
        all_clients = set()
        for c in contacts:
            for tag in (c.get("Client(s)") or "").split(","):
                t = tag.strip()
                if t: all_clients.add(t)
        for tag in sorted(all_clients, key=len, reverse=True):
            if re.search(r'\b' + re.escape(tag.lower()) + r'\b', text_lower):
                count = sum(1 for c in contacts
                            if tag in [t.strip() for t in (c.get("Client(s)") or "").split(",")])
                return f"There are **{count} contacts** tagged with **{tag}**.", [], "text"
        return f"There are **{len(contacts)} total contacts** in the database.", [], "text"

    # List building
    list_triggers = ["build a list", "build list", "create a list", "make a list",
                     "pull all", "get all", "get me all", "export all"]
    is_list_request = any(t in text_lower for t in list_triggers)

    client_match = None
    all_clients = set()
    for c in contacts:
        for tag in (c.get("Client(s)") or "").split(","):
            t = tag.strip()
            if t: all_clients.add(t)
    for tag in sorted(all_clients, key=len, reverse=True):
        if re.search(r'\b' + re.escape(tag.lower()) + r'\b', text_lower):
            client_match = tag
            break

    media_match = None
    media_map = {"broadcast": "Broadcast (TV)", "tv": "Broadcast (TV)",
                 "print": "Print & Online", "online": "Print & Online",
                 "radio": "Radio", "newsletter": "Newsletter", "podcast": "Podcast", "trade": "Trade Media"}
    for keyword, mt in media_map.items():
        if re.search(r'\b' + keyword + r'\b', text_lower):
            media_match = mt
            break

    market_match = None
    for m in ["local", "regional", "statewide", "national", "international"]:
        if re.search(r'\b' + m + r'\b', text_lower):
            market_match = m.capitalize()
            break

    if is_list_request and (client_match or media_match or market_match):
        matched = []
        for c in contacts:
            client_tags = [t.strip() for t in (c.get("Client(s)") or "").split(",")]
            if client_match and client_match not in client_tags: continue
            if media_match and c.get("Media Type") != media_match: continue
            if market_match and c.get("Market Type") != market_match: continue
            matched.append(c)
        if not matched:
            return "No contacts found matching those filters.", [], "text"
        desc = " ".join(filter(None, [
            media_match or "contacts",
            f"for {client_match}" if client_match else "",
            f"({market_match})" if market_match else ""
        ]))
        return f"Found **{len(matched)} {desc}**:", matched, "table_download"

    if "build a list with" in text_lower or "list with" in text_lower:
        clean = re.sub(r"build a (?:media )?list with|list with", "", text, flags=re.IGNORECASE)
        parts = re.split(r',|\band\b|&|\+', clean, flags=re.IGNORECASE)
        potential_names = [p.strip() for p in parts if p.strip()]
        matched = []
        not_found = []
        for name in potential_names:
            results = find_contacts_by_name(name, contacts)
            if results:
                for r in results:
                    if r not in matched: matched.append(r)
            else:
                not_found.append(name)
        if not matched:
            return "I couldn't find any of those contacts.", [], "text"
        msg = f"Found **{len(matched)} contact(s)**:"
        if not_found:
            msg += f"\n\n⚠️ Couldn't find: {', '.join(not_found)}"
        return msg, matched, "table_download"

    return ("I'm not sure how to help with that. Try:\n\n"
            "- *What is Ryan Lynch's email?*\n"
            "- *Do we have a contact from the Apopka Voice?*\n"
            "- *Build a list with Jane Dyer and Sam Martello*\n"
            "- *Pull all broadcast contacts for FAPIA*\n"
            "- *How many contacts do we have for LifeLink?*"), [], "text"


# ── Add Contact guided flow ───────────────────────────────────────────────────
ADD_STEPS = [
    ("outlet",      "What's the reporter's outlet?"),
    ("firstName",   "What's their first name?"),
    ("lastName",    "What's their last name?"),
    ("title",       "What's their title?"),
    ("email",       "What's their email? If you don't know, leave it blank."),
    ("phone",       "What's their phone number? If you don't know, leave it blank."),
    ("mediaType",   "What type of media is this? (e.g. Print & Online, Broadcast (TV), Radio, Newsletter, Podcast, Trade Media)"),
    ("clients",     "Which client(s) is this contact for? Select all that apply."),
    ("notes",       "Anything else worth noting before I add this contact? This will go in the Notes section. If nothing, leave it blank."),
]


def show():
    st.markdown("<br>", unsafe_allow_html=True)

    # Init session state
    if "bot_messages" not in st.session_state:
        st.session_state.bot_messages = []
    if "add_flow" not in st.session_state:
        st.session_state.add_flow = None  # None = not in flow, dict = in progress
    if "add_step" not in st.session_state:
        st.session_state.add_step = 0

    # ── Home screen buttons ───────────────────────────────────────────────
    if not st.session_state.bot_messages and not st.session_state.add_flow:
        col1, col2, col3 = st.columns([1, 4, 1])
        with col2:
            st.markdown("## What can I help you with?")
            st.markdown(" ")
            btn_cols = st.columns(2)
            with btn_cols[0]:
                if st.button("➕ Add Contact", use_container_width=True, type="primary"):
                    st.session_state.add_flow = {}
                    st.session_state.add_step = 0
                    st.session_state.bot_messages.append({
                        "role": "assistant",
                        "content": "Let's add a new contact! 🎉\n\n" + ADD_STEPS[0][1]
                    })
                    st.rerun()
                if st.button("📋 Build a List", use_container_width=True):
                    st.session_state.bot_messages.append({"role": "user", "content": "Build a list"})
                    st.session_state.bot_messages.append({"role": "assistant",
                        "content": "Sure! Try something like:\n- *Pull all broadcast contacts for FAPIA*\n- *Build a list with Ryan Lynch and Jane Dyer*\n- *Get all LifeLink contacts*"})
                    st.rerun()
            with btn_cols[1]:
                if st.button("🔍 Find a Contact", use_container_width=True):
                    st.session_state.bot_messages.append({"role": "user", "content": "Find a contact"})
                    st.session_state.bot_messages.append({"role": "assistant",
                        "content": "Sure! Try something like:\n- *What is Ryan Lynch's email?*\n- *Do we have a contact from the Orlando Sentinel?*\n- *Who is Sam Martello?*"})
                    st.rerun()
                if st.button("📊 Database Stats", use_container_width=True):
                    contacts = get_all_contacts()
                    from collections import Counter
                    mt_counts = Counter(c.get("Media Type","Unknown") for c in contacts)
                    lines = [f"**Total contacts: {len(contacts)}**\n"]
                    for mt, cnt in sorted(mt_counts.items()):
                        lines.append(f"- {mt}: {cnt}")
                    st.session_state.bot_messages.append({"role": "user", "content": "Database stats"})
                    st.session_state.bot_messages.append({"role": "assistant", "content": "\n".join(lines)})
                    st.rerun()

        st.markdown("---")

    # ── Chat history ──────────────────────────────────────────────────────
    for msg in st.session_state.bot_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("results") and msg.get("display") in ("table", "table_download"):
                COLS = ["Outlet","Contact First","Contact Last","Title","Email","Phone","Media Type","Client(s)"]
                rows = [{c: contact.get(c,"") or "" for c in COLS} for contact in msg["results"]]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=300)
            if msg.get("results") and msg.get("display") == "table_download":
                excel_bytes = build_excel(msg["results"], "Boulder Bot List")
                st.download_button(
                    label="⬇️ Download as Excel",
                    data=excel_bytes,
                    file_name="boulder_bot_list.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_{msg['key']}"
                )

    # ── Add Contact guided flow ───────────────────────────────────────────
    if st.session_state.add_flow is not None:
        step_idx = st.session_state.add_step

        if step_idx < len(ADD_STEPS):
            field_key, question = ADD_STEPS[step_idx]

            # Client multi-select step
            if field_key == "clients":
                with st.chat_message("assistant"):
                    st.markdown(question)
                    selected = st.multiselect("Select client(s):", CLIENTS, key="client_select")
                    if st.button("Continue →", type="primary"):
                        st.session_state.add_flow["clients"] = ", ".join(selected)
                        st.session_state.bot_messages.append({"role": "user", "content": ", ".join(selected) if selected else "None"})
                        st.session_state.add_step += 1
                        next_q = ADD_STEPS[st.session_state.add_step][1] if st.session_state.add_step < len(ADD_STEPS) else ""
                        if next_q:
                            st.session_state.bot_messages.append({"role": "assistant", "content": next_q})
                        st.rerun()
            else:
                # Regular text input step — handled via chat input below
                pass

        else:
            # All steps done — show confirmation
            flow = st.session_state.add_flow
            with st.chat_message("assistant"):
                st.markdown("Here's a summary — does everything look right?")
                col1, col2 = st.columns(2)
                with col1:
                    flow["outlet"]     = st.text_input("Outlet",      value=flow.get("outlet",""),     key="cf_outlet")
                    flow["firstName"]  = st.text_input("First Name",  value=flow.get("firstName",""),  key="cf_first")
                    flow["lastName"]   = st.text_input("Last Name",   value=flow.get("lastName",""),   key="cf_last")
                    flow["title"]      = st.text_input("Title",       value=flow.get("title",""),      key="cf_title")
                    flow["email"]      = st.text_input("Email",       value=flow.get("email",""),      key="cf_email")
                with col2:
                    flow["phone"]      = st.text_input("Phone",       value=flow.get("phone",""),      key="cf_phone")
                    flow["clients"]    = st.text_input("Client(s)",   value=flow.get("clients",""),    key="cf_clients")
                    flow["notes"]      = st.text_area("Notes",        value=flow.get("notes",""),      key="cf_notes", height=80)
                    media_idx = MEDIA_TYPES.index(flow.get("mediaType","Print & Online")) if flow.get("mediaType") in MEDIA_TYPES else 0
                    flow["mediaType"]  = st.selectbox("Media Type",   MEDIA_TYPES, index=media_idx,   key="cf_media")

                bcol1, bcol2 = st.columns(2)
                with bcol1:
                    if st.button("✅ Add to Database", type="primary"):
                        email = flow.get("email","").strip()
                        if not email:
                            email = ""
                        contact = {
                            "Outlet":        flow.get("outlet",""),
                            "Contact First": flow.get("firstName",""),
                            "Contact Last":  flow.get("lastName",""),
                            "Title":         flow.get("title",""),
                            "Email":         email,
                            "Phone":         flow.get("phone",""),
                            "Media Type":    flow.get("mediaType","Print & Online"),
                            "Client(s)":     flow.get("clients",""),
                            "Notes":         flow.get("notes",""),
                        }
                        with st.spinner("Adding to Airtable..."):
                            success, errors = create_contacts([contact])
                        if success:
                            name = f"{flow.get('firstName','')} {flow.get('lastName','')}".strip() or flow.get('outlet','')
                            st.session_state.bot_messages.append({
                                "role": "assistant",
                                "content": f"✅ **{name}** from **{flow.get('outlet','')}** has been added to the database!",
                                "key": len(st.session_state.bot_messages)
                            })
                            st.session_state.add_flow = None
                            st.session_state.add_step = 0
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(f"Something went wrong: {errors}")
                with bcol2:
                    if st.button("❌ Cancel"):
                        st.session_state.bot_messages.append({"role": "assistant", "content": "No problem — contact was not added."})
                        st.session_state.add_flow = None
                        st.session_state.add_step = 0
                        st.rerun()

    # ── Regular chat input ────────────────────────────────────────────────
    user_input = st.chat_input("Ask anything about your contacts...")

    if user_input:
        # Handle guided flow text steps
        if st.session_state.add_flow is not None and st.session_state.add_step < len(ADD_STEPS):
            field_key, _ = ADD_STEPS[st.session_state.add_step]
            if field_key != "clients":
                st.session_state.add_flow[field_key] = user_input
                st.session_state.bot_messages.append({"role": "user", "content": user_input})
                st.session_state.add_step += 1
                if st.session_state.add_step < len(ADD_STEPS):
                    next_q = ADD_STEPS[st.session_state.add_step][1]
                    st.session_state.bot_messages.append({"role": "assistant", "content": next_q})
                else:
                    st.session_state.bot_messages.append({"role": "assistant", "content": "Almost done! Review the details below and confirm."})
                st.rerun()
        else:
            # Normal chat
            st.session_state.bot_messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)
            with st.spinner("Thinking..."):
                contacts = get_all_contacts()
                response_text, matched, display = parse_request(user_input, contacts)
            with st.chat_message("assistant"):
                st.markdown(response_text)
                if matched and display in ("table", "table_download"):
                    COLS = ["Outlet","Contact First","Contact Last","Title","Email","Phone","Media Type","Client(s)"]
                    rows = [{c: contact.get(c,"") or "" for c in COLS} for contact in matched]
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=300)
                if matched and display == "table_download":
                    msg_key = len(st.session_state.bot_messages)
                    excel_bytes = build_excel(matched, "Boulder Bot List")
                    st.download_button(
                        label="⬇️ Download as Excel",
                        data=excel_bytes,
                        file_name="boulder_bot_list.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_{msg_key}"
                    )
            msg_key = len(st.session_state.bot_messages)
            st.session_state.bot_messages.append({
                "role": "assistant", "content": response_text,
                "results": matched, "display": display, "key": msg_key,
            })

    # Clear chat
    if st.session_state.bot_messages and not st.session_state.add_flow:
        if st.button("🗑️ Clear chat", key="clear"):
            st.session_state.bot_messages = []
            st.rerun()
