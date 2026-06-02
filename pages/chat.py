import streamlit as st
from utils.airtable import get_all_contacts
from utils.excel import build_excel
import re
import pandas as pd

def find_contacts_by_name(name, contacts):
    """Find contacts matching a name (full, first, or last)."""
    name_lower = name.lower().strip()
    name_parts = name_lower.split()
    matched = []
    for c in contacts:
        fn = (c.get("Contact First") or "").lower()
        ln = (c.get("Contact Last") or "").lower()
        full = f"{fn} {ln}".strip()
        if (name_lower == full or
            name_lower == fn or
            name_lower == ln or
            (len(name_parts) == 2 and name_parts[0] == fn and name_parts[1] == ln) or
            (len(name_parts) == 1 and (name_parts[0] == fn or name_parts[0] == ln))):
            matched.append(c)
    return matched

def parse_request(text, contacts):
    """Parse request and return (response_text, matched_contacts, show_table, allow_download)"""
    text_lower = text.lower().strip()

    # ── Single contact lookup questions ──────────────────────────────────
    # "What is X's email/phone/title/outlet?"
    info_patterns = [
        (r"what is (.+?)['']s (email|phone|title|outlet|number|website|market|client)", "field_lookup"),
        (r"what['']s (.+?)['']s (email|phone|title|outlet|number|website|market|client)", "field_lookup"),
        (r"(.+?)['']s (email|phone|title|outlet|number|website|market|client)", "field_lookup"),
        (r"(email|phone|title|outlet|number|website) (?:for|of) (.+)", "field_lookup_rev"),
        (r"find (.+)", "find"),
        (r"who is (.+)", "find"),
        (r"look up (.+)", "find"),
        (r"search for (.+)", "find"),
        (r"tell me about (.+)", "find"),
        (r"show me (.+?)['']s (.*)", "field_lookup"),
    ]

    field_map = {
        "email": "Email", "phone": "Phone", "number": "Phone",
        "title": "Title", "outlet": "Outlet", "website": "Website",
        "market": "Market", "client": "Client(s)",
    }

    for pattern, ptype in info_patterns:
        m = re.search(pattern, text_lower)
        if m:
            if ptype == "field_lookup":
                name_str = m.group(1).strip()
                field_str = m.group(2).strip()
                field = field_map.get(field_str, None)
                matched = find_contacts_by_name(name_str, contacts)
                if not matched:
                    return f"I couldn't find anyone named **{name_str.title()}** in the database.", [], False, False
                if field:
                    lines = []
                    for c in matched:
                        val = c.get(field, "") or "not on file"
                        name = f"{c.get('Contact First','')} {c.get('Contact Last','')}".strip() or c.get('Outlet','')
                        lines.append(f"**{name}** ({c.get('Outlet','')}) — {field}: **{val}**")
                    return "\n\n".join(lines), matched, False, False
                else:
                    return None, matched, True, False

            elif ptype == "field_lookup_rev":
                field_str = m.group(1).strip()
                name_str = m.group(2).strip()
                field = field_map.get(field_str, None)
                matched = find_contacts_by_name(name_str, contacts)
                if not matched:
                    return f"I couldn't find anyone named **{name_str.title()}** in the database.", [], False, False
                if field:
                    lines = []
                    for c in matched:
                        val = c.get(field, "") or "not on file"
                        name = f"{c.get('Contact First','')} {c.get('Contact Last','')}".strip() or c.get('Outlet','')
                        lines.append(f"**{name}** ({c.get('Outlet','')}) — {field}: **{val}**")
                    return "\n\n".join(lines), matched, False, False

            elif ptype == "find":
                name_str = m.group(1).strip()
                matched = find_contacts_by_name(name_str, contacts)
                if not matched:
                    return f"I couldn't find anyone named **{name_str.title()}** in the database.", [], False, False
                return f"Here's what I found for **{name_str.title()}**:", matched, True, False

    # ── How many questions ────────────────────────────────────────────────
    if "how many" in text_lower:
        # How many contacts for a client?
        all_clients = set()
        for c in contacts:
            for tag in (c.get("Client(s)") or "").split(","):
                t = tag.strip().lower()
                if t: all_clients.add(t)
        for tag in all_clients:
            if tag in text_lower:
                count = sum(1 for c in contacts if tag in [t.strip().lower() for t in (c.get("Client(s)") or "").split(",")])
                return f"There are **{count} contacts** tagged with **{tag.upper()}**.", [], False, False
        # How many broadcast/radio/etc?
        media_map = {"broadcast": "Broadcast (TV)", "tv": "Broadcast (TV)", "radio": "Radio",
                     "print": "Print & Online", "newsletter": "Newsletter", "podcast": "Podcast", "trade": "Trade Media"}
        for kw, mt in media_map.items():
            if kw in text_lower:
                count = sum(1 for c in contacts if c.get("Media Type") == mt)
                return f"There are **{count} {mt} contacts** in the database.", [], False, False
        total = len(contacts)
        return f"There are **{total} total contacts** in the database.", [], False, False

    # ── List building requests ────────────────────────────────────────────
    name_triggers = ["build a list with", "build a media list with", "build list with",
                     "pull", "get me", "create a list", "list with", "list for", "export"]

    # Client filter
    client_match = None
    all_clients = set()
    for c in contacts:
        for tag in (c.get("Client(s)") or "").split(","):
            t = tag.strip().lower()
            if t: all_clients.add(t)
    for tag in sorted(all_clients, key=len, reverse=True):
        if tag in text_lower:
            client_match = tag
            break

    # Media type filter
    media_match = None
    media_map = {"broadcast": "Broadcast (TV)", "tv": "Broadcast (TV)", "television": "Broadcast (TV)",
                 "print": "Print & Online", "online": "Print & Online",
                 "radio": "Radio", "newsletter": "Newsletter", "podcast": "Podcast", "trade": "Trade Media"}
    for keyword, mt in media_map.items():
        if keyword in text_lower:
            media_match = mt
            break

    # Market type filter
    market_match = None
    for m in ["local", "regional", "statewide", "national", "international"]:
        if m in text_lower:
            market_match = m.capitalize()
            break

    if client_match or media_match or market_match:
        matched = []
        for c in contacts:
            client_tags = [t.strip().lower() for t in (c.get("Client(s)") or "").split(",")]
            if client_match and client_match not in client_tags: continue
            if media_match and c.get("Media Type") != media_match: continue
            if market_match and c.get("Market Type") != market_match: continue
            matched.append(c)
        if not matched:
            return "I couldn't find any contacts matching those filters.", [], False, False
        desc = " ".join(filter(None, [
            media_match or "",
            f"contacts for {client_match.upper()}" if client_match else "contacts",
            f"({market_match})" if market_match else ""
        ]))
        return f"Found **{len(matched)} {desc}**:", matched, True, True

    # Name-based list building
    if any(t in text_lower for t in name_triggers):
        clean_text = text
        for t in sorted(name_triggers, key=len, reverse=True):
            clean_text = re.sub(t, "", clean_text, flags=re.IGNORECASE)
        parts = re.split(r',|and|&|\+', clean_text, flags=re.IGNORECASE)
        potential_names = [p.strip() for p in parts if p.strip()]
        matched = []
        not_found = []
        for name in potential_names:
            results = find_contacts_by_name(name, contacts)
            if results:
                for r in results:
                    if r not in matched:
                        matched.append(r)
            else:
                not_found.append(name)
        if not matched:
            return "I couldn't find any of those contacts. Double-check the names and try again.", [], False, False
        msg = f"Found **{len(matched)} contact(s)**:"
        if not_found:
            msg += f"\n\n⚠️ Couldn't find: {', '.join(not_found)}"
        return msg, matched, True, True

    # ── Fallback ──────────────────────────────────────────────────────────
    return ("I'm not sure how to answer that. Try asking things like:\n\n"
            "- *What is Ryan Lynch's email?*\n"
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
            "Build a list with Jane Dyer and Sam Martello",
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
            "role": "assistant",
            "content": response_text,
            "results": matched,
            "show_table": show_table,
            "allow_download": allow_download,
            "key": msg_key,
        })

    if st.session_state.bot_messages:
        if st.button("🗑️ Clear chat", key="clear"):
            st.session_state.bot_messages = []
            st.rerun()
