import streamlit as st
import requests
import json
from utils.airtable import get_all_contacts, create_contacts
from utils.excel import build_excel
import pandas as pd

CLIENTS = ["811", "Beacon College", "EA Orlando", "FAPIA", "LifeLink", "OIC", "SO"]
MEDIA_TYPES = ["Print & Online", "Broadcast (TV)", "Radio", "Newsletter", "Podcast", "Trade Media"]

SYSTEM_PROMPT = """You are Boulder, a PR assistant for Curley & Pynn, a public relations agency based in Orlando, Florida.

You have access to a media contacts database with 673 journalists and reporters. Your job is to help the team:
1. Find contacts and answer questions about them
2. Build targeted media lists
3. Add new contacts to the database
4. Write tailored pitches for specific reporters
5. Research reporters using web search

The database fields are: Outlet, Contact First, Contact Last, Title, Email, Phone, Market Type (Local/Regional/Statewide/National/International), Market, Media Type (Print & Online, Broadcast (TV), Radio, Newsletter, Podcast, Trade Media), Trade Sub, Client(s), Notes, Website.

Clients include: SO (Sarasota Orchestra), FAPIA (Florida Association of Insurance and Professionals), LifeLink (organ donation nonprofit), OIC (OIC Inspired), Beacon College, EA Orlando, and 811 (Sunshine 811).

When building media lists, think about which contacts would be most relevant based on their beat, outlet, and market.

When writing pitches, always:
- Reference the reporter's specific beat and recent coverage
- Keep it concise (3-4 short paragraphs max)
- Lead with the news hook
- Explain why this story is relevant to their audience
- End with a clear call to action

When you need to return structured data (like a list of contacts to display), format it as JSON inside <contacts> tags like this:
<contacts>[{"Outlet": "...", "Contact First": "...", ...}]</contacts>

When you want to add a contact to the database, format it as JSON inside <add_contact> tags:
<add_contact>{"Outlet": "...", "Contact First": "...", "Contact Last": "...", "Title": "...", "Email": "...", "Phone": "...", "Media Type": "...", "Client(s)": "...", "Notes": ""}</add_contact>

Always be helpful, professional, and concise. You represent a PR agency so your tone should match."""

def call_claude(messages, contacts_context=""):
    """Call Claude API with web search enabled."""
    api_key = st.secrets["ANTHROPIC_API_KEY"]
    
    system = SYSTEM_PROMPT
    if contacts_context:
        system += f"\n\nHere is the current contacts database for reference:\n{contacts_context}"
    
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2000,
        "system": system,
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "messages": messages
    }
    
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json=payload,
        timeout=60
    )
    resp.raise_for_status()
    return resp.json()

def extract_text(response):
    """Extract text content from Claude response."""
    text = ""
    for block in response.get("content", []):
        if block.get("type") == "text":
            text += block.get("text", "")
    return text

def extract_contacts_from_response(text):
    """Extract contact JSON from response if present."""
    import re
    match = re.search(r'<contacts>(.*?)</contacts>', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            return None
    return None

def extract_add_contact_from_response(text):
    """Extract add_contact JSON from response if present."""
    import re
    match = re.search(r'<add_contact>(.*?)</add_contact>', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            return None
    return None

def clean_response_text(text):
    """Remove XML tags from display text."""
    import re
    text = re.sub(r'<contacts>.*?</contacts>', '', text, flags=re.DOTALL)
    text = re.sub(r'<add_contact>.*?</add_contact>', '', text, flags=re.DOTALL)
    return text.strip()

def build_contacts_context(contacts):
    """Build a compact summary of contacts for Claude."""
    lines = []
    for c in contacts:
        name = f"{c.get('Contact First','')} {c.get('Contact Last','')}".strip()
        lines.append(f"{c.get('Outlet','')} | {name} | {c.get('Title','')} | {c.get('Email','')} | {c.get('Media Type','')} | {c.get('Client(s)','')} | {c.get('Market Type','')}")
    return "\n".join(lines)

def show():
    st.markdown("<br>", unsafe_allow_html=True)

    # Init session state
    if "bot_messages" not in st.session_state:
        st.session_state.bot_messages = []
    if "api_messages" not in st.session_state:
        st.session_state.api_messages = []
    if "pending_add_contact" not in st.session_state:
        st.session_state.pending_add_contact = None
    if "add_flow" not in st.session_state:
        st.session_state.add_flow = None
    if "add_step" not in st.session_state:
        st.session_state.add_step = 0

    ADD_STEPS = [
        ("outlet",      "What's the reporter's outlet?"),
        ("firstName",   "What's their first name?"),
        ("lastName",    "What's their last name?"),
        ("title",       "What's their title?"),
        ("email",       "What's their email? If you don't know, leave it blank."),
        ("phone",       "What's their phone number? If you don't know, leave it blank."),
        ("mediaType",   "What type of media is this? (e.g. Print & Online, Broadcast (TV), Radio, Newsletter, Podcast, Trade Media)"),
        ("clients",     "Which client(s) is this contact for? Select all that apply."),
        ("notes",       "Anything else worth noting? If nothing, leave it blank."),
    ]

    # Home screen
    if not st.session_state.bot_messages and not st.session_state.add_flow:
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            st.markdown("""
                <div style='text-align: center; margin-bottom: 2rem;'>
                    <img src='https://raw.githubusercontent.com/Ryan-Greene/media-contacts-app/main/c%26pboulder.png' width='160' style='margin-bottom: 1.5rem;'/>
                    <h2 style='font-weight: 600; margin: 0;'>Let's drive past this boulder.</h2>
                </div>
            """, unsafe_allow_html=True)
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
                    st.session_state.api_messages.append({"role": "user", "content": "Build a list"})
                    st.rerun()
            with btn_cols[1]:
                if st.button("🔍 Find a Contact", use_container_width=True):
                    st.session_state.bot_messages.append({"role": "user", "content": "Find a contact"})
                    st.session_state.api_messages.append({"role": "user", "content": "Find a contact"})
                    st.rerun()
                if st.button("✍️ Write a Pitch", use_container_width=True):
                    st.session_state.bot_messages.append({"role": "user", "content": "I need help writing a pitch"})
                    st.session_state.api_messages.append({"role": "user", "content": "I need help writing a pitch"})
                    st.rerun()

    st.markdown("---")

    # Display chat history
    for msg in st.session_state.bot_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("results"):
                COLS = ["Outlet","Contact First","Contact Last","Title","Email","Phone","Media Type","Client(s)"]
                rows = [{c: contact.get(c,"") or "" for c in COLS} for contact in msg["results"]]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=300)
            if msg.get("allow_download") and msg.get("results"):
                excel_bytes = build_excel(msg["results"], "Boulder List")
                st.download_button(
                    label="⬇️ Download as Excel",
                    data=excel_bytes,
                    file_name="boulder_list.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_{msg['key']}"
                )

    # Pending contact confirmation (from Claude suggestion)
    if st.session_state.pending_add_contact:
        pc = st.session_state.pending_add_contact
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
                media_opts = MEDIA_TYPES
                idx = media_opts.index(pc.get("Media Type","Print & Online")) if pc.get("Media Type") in media_opts else 0
                pc["Media Type"]  = st.selectbox("Media Type", media_opts, index=idx, key="pc_media")
            bcol1, bcol2 = st.columns(2)
            with bcol1:
                if st.button("✅ Add to Database", type="primary"):
                    with st.spinner("Adding..."):
                        success, errors = create_contacts([pc])
                    if success:
                        name = f"{pc.get('Contact First','')} {pc.get('Contact Last','')}".strip() or pc.get('Outlet','')
                        st.session_state.bot_messages.append({"role": "assistant", "content": f"✅ **{name}** added to the database!", "key": len(st.session_state.bot_messages)})
                        st.session_state.pending_add_contact = None
                        st.cache_data.clear()
                        st.rerun()
            with bcol2:
                if st.button("❌ Cancel"):
                    st.session_state.pending_add_contact = None
                    st.session_state.bot_messages.append({"role": "assistant", "content": "No problem — contact was not added.", "key": len(st.session_state.bot_messages)})
                    st.rerun()

    # Guided Add Contact flow
    if st.session_state.add_flow is not None:
        step_idx = st.session_state.add_step
        if step_idx < len(ADD_STEPS):
            field_key, question = ADD_STEPS[step_idx]
            if field_key == "clients":
                with st.chat_message("assistant"):
                    st.markdown(question)
                    selected = st.multiselect("Select client(s):", CLIENTS, key="client_select")
                    if st.button("Continue →", type="primary"):
                        st.session_state.add_flow["clients"] = ", ".join(selected)
                        st.session_state.bot_messages.append({"role": "user", "content": ", ".join(selected) if selected else "None"})
                        st.session_state.add_step += 1
                        if st.session_state.add_step < len(ADD_STEPS):
                            st.session_state.bot_messages.append({"role": "assistant", "content": ADD_STEPS[st.session_state.add_step][1]})
                        st.rerun()
        else:
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
                        contact = {
                            "Outlet":        flow.get("outlet",""),
                            "Contact First": flow.get("firstName",""),
                            "Contact Last":  flow.get("lastName",""),
                            "Title":         flow.get("title",""),
                            "Email":         flow.get("email",""),
                            "Phone":         flow.get("phone",""),
                            "Media Type":    flow.get("mediaType","Print & Online"),
                            "Client(s)":     flow.get("clients",""),
                            "Notes":         flow.get("notes",""),
                        }
                        with st.spinner("Adding to Airtable..."):
                            success, errors = create_contacts([contact])
                        if success:
                            name = f"{flow.get('firstName','')} {flow.get('lastName','')}".strip() or flow.get('outlet','')
                            st.session_state.bot_messages.append({"role": "assistant", "content": f"✅ **{name}** from **{flow.get('outlet','')}** added!", "key": len(st.session_state.bot_messages)})
                            st.session_state.add_flow = None
                            st.session_state.add_step = 0
                            st.cache_data.clear()
                            st.rerun()
                with bcol2:
                    if st.button("❌ Cancel"):
                        st.session_state.bot_messages.append({"role": "assistant", "content": "No problem — contact was not added."})
                        st.session_state.add_flow = None
                        st.session_state.add_step = 0
                        st.rerun()

    # Chat input
    user_input = st.chat_input("Ask anything — find contacts, build lists, write pitches...")

    if user_input:
        # Handle guided flow text steps
        if st.session_state.add_flow is not None and st.session_state.add_step < len(ADD_STEPS):
            field_key, _ = ADD_STEPS[st.session_state.add_step]
            if field_key != "clients":
                st.session_state.add_flow[field_key] = user_input
                st.session_state.bot_messages.append({"role": "user", "content": user_input})
                st.session_state.add_step += 1
                if st.session_state.add_step < len(ADD_STEPS):
                    st.session_state.bot_messages.append({"role": "assistant", "content": ADD_STEPS[st.session_state.add_step][1]})
                else:
                    st.session_state.bot_messages.append({"role": "assistant", "content": "Almost done! Review the details below and confirm."})
                st.rerun()
        else:
            # Normal Claude API chat
            st.session_state.bot_messages.append({"role": "user", "content": user_input})
            st.session_state.api_messages.append({"role": "user", "content": user_input})

            with st.chat_message("user"):
                st.markdown(user_input)

            with st.spinner("Thinking..."):
                try:
                    contacts = get_all_contacts()
                    contacts_context = build_contacts_context(contacts)
                    response = call_claude(st.session_state.api_messages, contacts_context)
                    raw_text = extract_text(response)
                    display_text = clean_response_text(raw_text)
                    extracted_contacts = extract_contacts_from_response(raw_text)
                    add_contact_data = extract_add_contact_from_response(raw_text)

                    # Add assistant response to API history
                    st.session_state.api_messages.append({"role": "assistant", "content": raw_text})

                    with st.chat_message("assistant"):
                        st.markdown(display_text)
                        if extracted_contacts:
                            COLS = ["Outlet","Contact First","Contact Last","Title","Email","Phone","Media Type","Client(s)"]
                            rows = [{c: contact.get(c,"") or "" for c in COLS} for contact in extracted_contacts]
                            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=300)
                            excel_bytes = build_excel(extracted_contacts, "Boulder List")
                            msg_key = len(st.session_state.bot_messages)
                            st.download_button(
                                label="⬇️ Download as Excel",
                                data=excel_bytes,
                                file_name="boulder_list.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"dl_{msg_key}"
                            )

                    if add_contact_data:
                        st.session_state.pending_add_contact = add_contact_data

                    msg_key = len(st.session_state.bot_messages)
                    st.session_state.bot_messages.append({
                        "role": "assistant",
                        "content": display_text,
                        "results": extracted_contacts,
                        "allow_download": bool(extracted_contacts),
                        "key": msg_key,
                    })
                    st.rerun()

                except Exception as e:
                    error_msg = f"Something went wrong: {str(e)}"
                    st.session_state.bot_messages.append({"role": "assistant", "content": error_msg})
                    with st.chat_message("assistant"):
                        st.markdown(error_msg)

    # Clear chat
    if st.session_state.bot_messages and not st.session_state.add_flow and not st.session_state.pending_add_contact:
        if st.button("🗑️ Clear chat", key="clear"):
            st.session_state.bot_messages = []
            st.session_state.api_messages = []
            st.rerun()
