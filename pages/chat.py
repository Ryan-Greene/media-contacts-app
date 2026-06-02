import streamlit as st
from utils.airtable import get_all_contacts, create_contacts
from utils.excel import build_excel
import re
import pandas as pd

# ── Contact parsing ───────────────────────────────────────────────────────────
def parse_new_contact(text):
    """Try to extract contact details from a plain English add request."""
    result = {}
    t = text

    # Email
    email_m = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', t)
    if email_m:
        result["Email"] = email_m.group(0)
        t = t.replace(result["Email"], "")

    # Phone
    phone_m = re.search(r'(\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4})', t)
    if phone_m:
        result["Phone"] = phone_m.group(0)
        t = t.replace(result["Phone"], "")

    # Outlet — "from/at/with X" or "at X"
    outlet_m = re.search(r'(?:from|at|with|for)\s+(?:the\s+)?([A-Z][^,\.]+?)(?:,|\.|she|he|they|her|his|is a|works|covers|\s+and\b|$)', t)
    if outlet_m:
        result["Outlet"] = outlet_m.group(1).strip()

    # Name — look for two capitalized words near the start
    name_m = re.search(r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b', text)
    if name_m:
        result["Contact First"] = name_m.group(1)
        result["Contact Last"]  = name_m.group(2)

    # Title — "she's a X", "he is a X", "is a X", "works as X"
    title_m = re.search(r'(?:she\'s|he\'s|they\'re|is a|is an|works as a?|her title is|his title is)\s+([^,\.]+?)(?:,|\.|at|for|from|$)', t, re.IGNORECASE)
    if title_m:
        result["Title"] = title_m.group(1).strip()

    # Media type hints
    t_lower = text.lower()
    media_map = {
        "tv": "Broadcast (TV)", "television": "Broadcast (TV)", "broadcast": "Broadcast (TV)",
        "radio": "Radio", "podcast": "Podcast", "newsletter": "Newsletter",
        "print": "Print & Online", "online": "Print & Online", "trade": "Trade Media",
    }
    for kw, mt in media_map.items():
        if kw in t_lower:
            result["Media Type"] = mt
            break
    if "Media Type" not in result:
        result["Media Type"] = "Print & Online"

    # Client tags
    known_clients = ["SO", "FAPIA", "LifeLink", "OIC", "811", "Beacon College", "EA Orlando"]
    for client in known_clients:
        if re.search(r'\b' + re.escape(client) + r'\b', text, re.IGNORECASE):
            result["Client(s)"] = client
            break

    return result

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
    o = re.sub(r'^the\s+', '', outlet_name.lower().strip(), flags=re.IGNORECASE)
    return [c for c in contacts if o in (c.get("Outlet") or "").lower()]

def parse_request(text, contacts):
    text_lower = text.lower().strip()

    # ── Add contact detection ─────────────────────────────────────────────
    add_triggers = ["add ", "new contact", "add a contact", "add contact",
                    "create a contact", "put in ", "add to the database"]
    if any(t in text_lower for t in add_triggers):
        parsed = parse_new_contact(text)
        return None, None, "add_confirm", parsed

    # ── Outlet lookup ─────────────────────────────────────────────────────
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
                return f"I don't see any contacts from **{outlet_name.title()}** in the database.", [], "text", None
            return f"Found **{len(matched)} contact(s)** from **{outlet_name.title()}**:", matched, "table", None

    # ── Field lookup ──────────────────────────────────────────────────────
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
            return f"I couldn't find anyone named **{name_str.title()}** in the database.", [], "text", None
        lines = []
        for c in matched:
            val = c.get(field, "") or "not on file"
            name = f"{c.get('Contact First','')} {c.get('Contact Last','')}".strip() or c.get('Outlet','')
            lines.append(f"**{name}** ({c.get('Outlet','')}) — {field}: **{val}**")
        return "\n\n".join(lines), [], "text", None

    poss_pattern = r"(.+?)(?:'s|s') (email|phone|number|title|outlet|website)"
    m = re.search(poss_pattern, text_lower)
    if m:
        name_str = m.group(1).strip()
        field = field_map.get(m.group(2).strip())
        matched = find_contacts_by_name(name_str, contacts)
        if not matched:
            return f"I couldn't find anyone named **{name_str.title()}** in the database.", [], "text", None
        lines = []
        for c in matched:
            val = c.get(field, "") or "not on file"
            name = f"{c.get('Contact First','')} {c.get('Contact Last','')}".strip() or c.get('Outlet','')
            lines.append(f"**{name}** ({c.get('Outlet','')}) — {field}: **{val}**")
        return "\n\n".join(lines), [], "text", None

    # ── Find person ───────────────────────────────────────────────────────
    find_patterns = [r"(?:find|look up|search for|tell me about|who is|show me) (.+?)(?:\?|$)"]
    for pattern in find_patterns:
        m = re.search(pattern, text_lower)
        if m:
            name_str = m.group(1).strip().rstrip("?").strip()
            matched = find_contacts_by_name(name_str, contacts)
            if matched:
                return f"Here's what I found for **{name_str.title()}**:", matched, "table", None
            outlet_matched = find_contacts_by_outlet(name_str, contacts)
            if outlet_matched:
                return f"Found **{len(outlet_matched)} contact(s)** at **{name_str.title()}**:", outlet_matched, "table", None
            return f"I couldn't find **{name_str.title()}** in the database.", [], "text", None

    # ── How many ──────────────────────────────────────────────────────────
    if "how many" in text_lower:
        media_map = {"broadcast": "Broadcast (TV)", "tv": "Broadcast (TV)", "radio": "Radio",
                     "print": "Print & Online", "newsletter": "Newsletter",
                     "podcast": "Podcast", "trade": "Trade Media"}
        for kw, mt in media_map.items():
            if kw in text_lower:
                count = sum(1 for c in contacts if c.get("Media Type") == mt)
                return f"There are **{count} {mt} contacts** in the database.", [], "text", None
        all_clients = set()
        for c in contacts:
            for tag in (c.get("Client(s)") or "").split(","):
                t = tag.strip()
                if t: all_clients.add(t)
        for tag in sorted(all_clients, key=len, reverse=True):
            if re.search(r'\b' + re.escape(tag.lower()) + r'\b', text_lower):
                count = sum(1 for c in contacts
                            if tag in [t.strip() for t in (c.get("Client(s)") or "").split(",")])
                return f"There are **{count} contacts** tagged with **{tag}**.", [], "text", None
        return f"There are **{len(contacts)} total contacts** in the database.", [], "text", None

    # ── List building ─────────────────────────────────────────────────────
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
            return "No contacts found matching those filters.", [], "text", None
        desc = " ".join(filter(None, [
            media_match or "contacts",
            f"for {client_match}" if client_match else "",
            f"({market_match})" if market_match else ""
        ]))
        return f"Found **{len(matched)} {desc}**:", matched, "table_download", None

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
            return "I couldn't find any of those contacts.", [], "text", None
        msg = f"Found **{len(matched)} contact(s)**:"
        if not_found:
            msg += f"\n\n⚠️ Couldn't find: {', '.join(not_found)}"
        return msg, matched, "table_download", None

    return ("I'm not sure how to help with that. Try:\n\n"
            "- *Add Jane Smith from the Orlando Sentinel, reporter, jsmith@orlandosentinel.com*\n"
            "- *What is Ryan Lynch's email?*\n"
            "- *Do we have a contact from the Apopka Voice?*\n"
            "- *Build a list with Jane Dyer and Sam Martello*\n"
            "- *Pull all broadcast contacts for FAPIA*\n"
            "- *How many contacts do we have for LifeLink?*"), [], "text", None


def show():
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        st.markdown("## What can I help you with?")
        st.markdown(" ")
        examples = [
            "What is Ryan Lynch's email?",
            "Add Jane Smith, reporter at Orlando Sentinel, jsmith@orlandosentinel.com",
            "Pull all broadcast contacts for FAPIA",
            "How many contacts do we have for LifeLink?",
        ]
        chip_cols = st.columns(2)
        for i, ex in enumerate(examples):
            with chip_cols[i % 2]:
                if st.button(ex, use_container_width=True, key=f"chip_{i}"):
                    st.session_state.prefill = ex

    st.markdown("---")

    if "bot_messages" not in st.session_state:
        st.session_state.bot_messages = []
    if "pending_contact" not in st.session_state:
        st.session_state.pending_contact = None

    # Display chat history
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

    # Pending contact confirmation
    if st.session_state.pending_contact:
        pc = st.session_state.pending_contact
        with st.chat_message("assistant"):
            st.markdown("Here's what I parsed — does this look right?")
            col1, col2 = st.columns(2)
            with col1:
                pc["Contact First"] = st.text_input("First Name", value=pc.get("Contact First",""), key="pc_first")
                pc["Contact Last"]  = st.text_input("Last Name",  value=pc.get("Contact Last",""),  key="pc_last")
                pc["Title"]         = st.text_input("Title",       value=pc.get("Title",""),         key="pc_title")
                pc["Email"]         = st.text_input("Email",       value=pc.get("Email",""),         key="pc_email")
            with col2:
                pc["Outlet"]      = st.text_input("Outlet",     value=pc.get("Outlet",""),     key="pc_outlet")
                pc["Phone"]       = st.text_input("Phone",      value=pc.get("Phone",""),      key="pc_phone")
                pc["Client(s)"]   = st.text_input("Client(s)",  value=pc.get("Client(s)",""),  key="pc_clients")
                media_opts = ["Print & Online","Broadcast (TV)","Radio","Newsletter","Podcast","Trade Media"]
                idx = media_opts.index(pc.get("Media Type","Print & Online")) if pc.get("Media Type") in media_opts else 0
                pc["Media Type"]  = st.selectbox("Media Type", media_opts, index=idx, key="pc_media")

            bcol1, bcol2 = st.columns(2)
            with bcol1:
                if st.button("✅ Confirm & Add to Airtable", type="primary"):
                    if not pc.get("Email"):
                        st.error("Email is required.")
                    else:
                        with st.spinner("Adding contact..."):
                            success, errors = create_contacts([pc])
                        if success:
                            name = f"{pc.get('Contact First','')} {pc.get('Contact Last','')}".strip() or pc.get('Outlet','')
                            st.session_state.bot_messages.append({
                                "role": "assistant",
                                "content": f"✅ **{name}** has been added to Airtable!",
                                "key": len(st.session_state.bot_messages)
                            })
                            st.session_state.pending_contact = None
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(f"Something went wrong: {errors}")
            with bcol2:
                if st.button("❌ Cancel"):
                    st.session_state.bot_messages.append({
                        "role": "assistant",
                        "content": "No problem — contact was not added.",
                        "key": len(st.session_state.bot_messages)
                    })
                    st.session_state.pending_contact = None
                    st.rerun()

    # Chat input
    prefill = st.session_state.pop("prefill", "") if "prefill" in st.session_state else ""
    user_input = st.chat_input("Ask anything about your contacts...")
    if not user_input and prefill:
        user_input = prefill

    if user_input and not st.session_state.pending_contact:
        st.session_state.bot_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.spinner("Thinking..."):
            contacts = get_all_contacts()
            response_text, matched, display, parsed_contact = parse_request(user_input, contacts)

        if display == "add_confirm":
            st.session_state.pending_contact = parsed_contact
            st.session_state.bot_messages.append({
                "role": "assistant",
                "content": "Here's what I parsed — does this look right?",
                "key": len(st.session_state.bot_messages)
            })
            st.rerun()
        else:
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

    if st.session_state.bot_messages and not st.session_state.pending_contact:
        if st.button("🗑️ Clear chat", key="clear"):
            st.session_state.bot_messages = []
            st.rerun()
