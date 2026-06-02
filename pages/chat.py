import streamlit as st
from utils.airtable import get_all_contacts
from utils.excel import build_excel
import re
import pandas as pd

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
    o = outlet_name.lower().strip()
    return [c for c in contacts if o in (c.get("Outlet") or "").lower()]

def parse_request(text, contacts):
    text_lower = text.lower().strip()

    # ── Outlet lookup ─────────────────────────────────────────────────────
    # "Do we have a contact from X?" / "Do we have contacts at X?"
    outlet_patterns = [
        r"contact(?:s)? (?:from|at|with|for) (.+?)(?:\?|$)",
        r"anyone (?:from|at) (.+?)(?:\?|$)",
        r"who (?:do we have )?(?:from|at) (.+?)(?:\?|$)",
        r"contacts? (?:from|at) (.+?)(?:\?|$)",
    ]
    for pattern in outlet_patterns:
        m = re.search(pattern, text_lower)
        if m:
            outlet_name = m.group(1).strip().rstrip("?").strip()
            matched = find_contacts_by_outlet(outlet_name, contacts)
            if not matched:
                return f"I don't see any contacts from **{outlet_name.title()}** in the database.", [], False, False
            return f"Found **{len(matched)} contact(s)** from **{outlet_name.title()}**:", matched, True, False

    # ── Single field lookup ───────────────────────────────────────────────
    field_map = {
        "email": "Email", "phone": "Phone", "number": "Phone",
        "title": "Title", "outlet": "Outlet", "website": "Website",
        "market": "Market", "client": "Client(s)",
    }
    field_pattern = r"(?:what is|what's|get|find|show)(?: me)? (.+?)(?:'s|s') (email|phone|number|title|outlet|website|market|client)"
    m = re.search(field_pattern, text_lower)
    if m:
        name_str = m.group(1).strip()
        field_str = m.group(2).strip()
        field = field_map.get(field_str)
        matched = find_contacts_by_name(name_str, contacts)
        if not matched:
            return f"I couldn't find anyone named **{name_str.title()}** in the database.", [], False, False
        lines = []
        for c in matched:
            val = c.get(field, "") or "not on file"
            name = f"{c.get('Contact First','')} {c.get('Contact Last','')}".strip() or c.get('Outlet','')
            lines.append(f"**{name}** ({c.get('Outlet','')}) — {field}: **{val}**")
        return "\n\n".join(lines), [], False, False

    # Possessive pattern: "Ryan Lynch's email"
    poss_pattern = r"(.+?)(?:'s|s') (email|phone|number|title|outlet|website)"
    m = re.search(poss_pattern, text_lower)
    if m:
        name_str = m.group(1).strip()
        field_str = m.group(2).strip()
        field = field_map.get(field_str)
        matched = find_contacts_by_name(name_str, contacts)
        if not matched:
            return f"I couldn't find anyone named **{name_str.title()}** in the database.", [], False, False
        lines = []
        for c in matched:
            val = c.get(field, "") or "not on file"
            name = f"{c.get('Contact First','')} {c.get('Contact Last','')}".strip() or c.get('Outlet','')
            lines.append(f"**{name}** ({c.get('Outlet','')}) — {field}: **{val}**")
        return "\n\n".join(lines), [], False, False

    # ── Find/look up a person ─────────────────────────────────────────────
    find_patterns = [
        r"(?:find|look up|search for|tell me about|who is|show me) (.+?)(?:\?|$)",
    ]
    for pattern in find_patterns:
        m = re.search(pattern, text_lower)
        if m:
            name_str = m.group(1).strip().rstrip("?").strip()
            matched = find_contacts_by_name(name_str, contacts)
            if matched:
                return f"Here's what I found for **{name_str.title()}**:", matched, True, False
            # Try outlet
            outlet_matched = find_contacts_by_outlet(name_str, contacts)
            if outlet_matched:
                return f"Found **{len(outlet_matched)} contact(s)** at **{name_str.title()}**:", outlet_matched, True, False
            return f"I couldn't find **{name_str.title()}** in the database.", [], False, False

    # ── How many ──────────────────────────────────────────────────────────
    if "how many" in text_lower:
        media_map = {"broadcast": "Broadcast (TV)", "tv": "Broadcast (TV)", "radio": "Radio",
                     "print": "Print & Online", "newsletter": "Newsletter",
                     "podcast": "Podcast", "trade": "Trade Media"}
        for kw, mt in media_map.items():
            if kw in text_lower:
                count = sum(1 for c in contacts if c.get("Media Type") == mt)
                return f"There are **{count} {mt} contacts** in the database.", [], False, False
        # Client — use word boundary matching
        all_clients = set()
        for c in contacts:
            for tag in (c.get("Client(s)") or "").split(","):
                t = tag.strip()
                if t: all_clients.add(t)
        for tag in sorted(all_clients, key=len, reverse=True):
            if re.search(r'\b' + re.escape(tag.lower()) + r'\b', text_lower):
                count = sum(1 for c in contacts
                            if tag in [t.strip() for t in (c.get("Client(s)") or "").split(",")])
                return f"There are **{count} contacts** tagged with **{tag}**.", [], False, False
        return f"There are **{len(contacts)} total contacts** in the database.", [], False, False

    # ── List building ─────────────────────────────────────────────────────
    list_triggers = ["build a list", "build list", "create a list", "make a list",
                     "pull all", "get all", "get me all", "export all", "pull contacts", "get contacts"]
    is_list_request = any(t in text_lower for t in list_triggers)

    # Client — word boundary match only
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
    media_map = {"broadcast": "Broadcast (TV)", "tv": "Broadcast (TV)", "television": "Broadcast (TV)",
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
            return "No contacts found matching those filters.", [], False, False
        desc = " ".join(filter(None, [
            media_match or "contacts",
            f"for {client_match}" if client_match else "",
            f"({market_match})" if market_match else ""
        ]))
        return f"Found **{len(matched)} {desc}**:", matched, True, True

    # Name-based list
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
            return "I couldn't find any of those contacts. Double-check the names and try again.", [], False, False
        msg = f"Found **{len(matched)} contact(s)**:"
        if not_found:
            msg += f"\n\n⚠️ Couldn't find: {', '.join(not_found)}"
        return msg, matched, True, True

    # ── Fallback ──────────────────────────────────────────────────────────
    return ("I'm not sure how to help with that. Try:\n\n"
            "- *What is Ryan Lynch's email?*\n"
            "- *Do we have a contact from the Apopka Voice?*\n"
            "- *Build a list with Jane Dyer and Sam Martello*\n"
            "- *Pull all broadcast contacts for FAPIA*\n"
            "- *How many contacts do we have for LifeLink?*"), [], False, False


def show():
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        st.markdown("## What can I help you with?")
        st.markdown(" ")
        examples = [
            "What is Ryan Lynch's email?",
            "Do we have a contact from the Apopka Voice?",
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

    for msg in st.session_state.bot_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("results") and msg.get("show_table"):
                COLS = ["Outlet","Contact First","Contact Last","Title","Email","Phone","Media Type","Client(s)"]
                rows = [{c: contact.get(c,"") or "" for c in COLS} for contact in msg["results"]]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=300)
            if msg.get("results") and msg.get("allow_download"):
                excel_bytes = build_excel(msg["results"], "Boulder Bot List")
                st.download_button(
                    label="⬇️ Download as Excel",
                    data=excel_bytes,
                    file_name="boulder_bot_list.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_{msg['key']}"
                )

    prefill = st.session_state.pop("prefill", "") if "prefill" in st.session_state else ""
    user_input = st.chat_input("Ask anything about your contacts...")
    if not user_input and prefill:
        user_input = prefill

    if user_input:
        st.session_state.bot_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.spinner("Searching..."):
            contacts = get_all_contacts()
            response_text, matched, show_table, allow_download = parse_request(user_input, contacts)

        with st.chat_message("assistant"):
            st.markdown(response_text)
            if matched and show_table:
                COLS = ["Outlet","Contact First","Contact Last","Title","Email","Phone","Media Type","Client(s)"]
                rows = [{c: contact.get(c,"") or "" for c in COLS} for contact in matched]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=300)
            if matched and allow_download:
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
            "results": matched, "show_table": show_table,
            "allow_download": allow_download, "key": msg_key,
        })

    if st.session_state.bot_messages:
        if st.button("🗑️ Clear chat", key="clear"):
            st.session_state.bot_messages = []
            st.rerun()
