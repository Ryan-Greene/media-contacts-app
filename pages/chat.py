import streamlit as st
from utils.airtable import get_all_contacts
from utils.excel import build_excel
import re
import pandas as pd

def parse_request(text, contacts):
    text_lower = text.lower().strip()
    matched = []

    name_triggers = ["build a list with", "build a media list with", "build list with",
                     "pull", "get me", "add", "include", "list with", "list for"]

    # Client filter
    client_match = None
    all_clients = set()
    for c in contacts:
        for tag in (c.get("Client(s)") or "").split(","):
            t = tag.strip().lower()
            if t: all_clients.add(t)
    for tag in all_clients:
        if tag in text_lower:
            client_match = tag
            break

    # Media type filter
    media_match = None
    media_map = {
        "broadcast": "Broadcast (TV)", "tv": "Broadcast (TV)", "television": "Broadcast (TV)",
        "print": "Print & Online", "online": "Print & Online",
        "radio": "Radio", "newsletter": "Newsletter", "podcast": "Podcast",
        "trade": "Trade Media",
    }
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

    # Filter-based
    if client_match or media_match or market_match:
        for c in contacts:
            client_tags = [t.strip().lower() for t in (c.get("Client(s)") or "").split(",")]
            if client_match and client_match not in client_tags: continue
            if media_match and c.get("Media Type") != media_match: continue
            if market_match and c.get("Market Type") != market_match: continue
            matched.append(c)
        return matched, "filter"

    # Name-based
    clean_text = text
    for t in sorted(name_triggers, key=len, reverse=True):
        clean_text = re.sub(t, "", clean_text, flags=re.IGNORECASE)
    parts = re.split(r',|and|&|\+', clean_text, flags=re.IGNORECASE)
    potential_names = [p.strip() for p in parts if p.strip()]

    for name in potential_names:
        name_lower = name.lower()
        name_parts = name_lower.split()
        for c in contacts:
            fn = (c.get("Contact First") or "").lower()
            ln = (c.get("Contact Last") or "").lower()
            full = f"{fn} {ln}".strip()
            outlet = (c.get("Outlet") or "").lower()
            if (name_lower == full or name_lower == fn or name_lower == ln or
                (len(name_parts) == 2 and name_parts[0] == fn and name_parts[1] == ln) or
                name_lower in outlet):
                if c not in matched:
                    matched.append(c)

    return matched, "name"


def show():
    # ── Clean home screen ─────────────────────────────────────────────────
    st.markdown("<br><br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        st.markdown("## What can I help you with?")
        st.markdown(" ")

        # Example prompt chips
        examples = [
            "Build a list with Jane Dyer and Ryan Lynch",
            "Pull all broadcast contacts for FAPIA",
            "Get me all LifeLink contacts",
            "Get all national contacts for SO",
        ]
        chip_cols = st.columns(2)
        for i, ex in enumerate(examples):
            with chip_cols[i % 2]:
                if st.button(ex, use_container_width=True, key=f"chip_{i}"):
                    st.session_state.prefill = ex

    st.markdown("---")

    # ── Chat history ──────────────────────────────────────────────────────
    if "bot_messages" not in st.session_state:
        st.session_state.bot_messages = []
    if "prefill" not in st.session_state:
        st.session_state.prefill = ""

    for msg in st.session_state.bot_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("results"):
                COLS = ["Outlet","Contact First","Contact Last","Title","Email","Media Type","Client(s)"]
                rows = [{c: contact.get(c,"") or "" for c in COLS} for contact in msg["results"]]
                st.dataframe(pd.DataFrame(rows), use_container_width=True,
                             hide_index=True, height=300)
                excel_bytes = build_excel(msg["results"], "Boulder Bot List")
                st.download_button(
                    label="⬇️ Download as Excel",
                    data=excel_bytes,
                    file_name="boulder_bot_list.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_{msg['key']}"
                )

    # ── Chat input ────────────────────────────────────────────────────────
    prefill = st.session_state.pop("prefill", "") if "prefill" in st.session_state else ""
    user_input = st.chat_input("Ask Boulder Bot to build a list...")

    if not user_input and prefill:
        user_input = prefill

    if user_input:
        st.session_state.bot_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.spinner("Searching..."):
            contacts = get_all_contacts()
            matched, match_type = parse_request(user_input, contacts)

        with st.chat_message("assistant"):
            if not matched:
                response = "I couldn't find any contacts matching that request. Try a name, client tag (FAPIA, SO, LifeLink, etc.), or media type (broadcast, radio, print, etc.)."
                st.markdown(response)
                st.session_state.bot_messages.append({"role": "assistant", "content": response})
            else:
                response = f"Found **{len(matched)} contact(s)**:"
                st.markdown(response)
                COLS = ["Outlet","Contact First","Contact Last","Title","Email","Media Type","Client(s)"]
                rows = [{c: contact.get(c,"") or "" for c in COLS} for contact in matched]
                st.dataframe(pd.DataFrame(rows), use_container_width=True,
                             hide_index=True, height=300)
                excel_bytes = build_excel(matched, "Boulder Bot List")
                msg_key = len(st.session_state.bot_messages)
                st.download_button(
                    label="⬇️ Download as Excel",
                    data=excel_bytes,
                    file_name="boulder_bot_list.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_{msg_key}"
                )
                st.session_state.bot_messages.append({
                    "role": "assistant",
                    "content": response,
                    "results": matched,
                    "key": msg_key,
                })

    if st.session_state.bot_messages:
        if st.button("🗑️ Clear chat", key="clear"):
            st.session_state.bot_messages = []
            st.rerun()
