import streamlit as st
import requests
import json
from utils.airtable import get_all_contacts, create_contacts, append_pitch_history, find_contact_by_name
from utils.excel import build_excel
import pandas as pd

CLIENTS = ["811", "Beacon College", "EA Orlando", "FAPIA", "LifeLink", "OIC", "SO"]
MEDIA_TYPES = ["Print & Online", "Broadcast (TV)", "Radio", "Newsletter", "Podcast", "Trade Media"]

SYSTEM_PROMPT = """You are Boulder, a PR assistant for Curley & Pynn, a public relations agency based in Orlando, Florida.

You have access to a media contacts database with 673 journalists and reporters. Your job is to help the team with four main tasks: adding contacts, building media lists, finding contact information, and writing tailored pitches.

The database fields are: Outlet, Contact First, Contact Last, Title, Email, Phone, Market Type (Local/Regional/Statewide/National/International), Market, Media Type (Print & Online, Broadcast (TV), Radio, Newsletter, Podcast, Trade Media), Trade Sub, Client(s), Notes, Website.

Clients:
- SO = Sarasota Orchestra (classical music, arts, culture)
- FAPIA = Florida Association of Insurance Professionals (insurance industry)
- LifeLink = organ and tissue donation nonprofit
- OIC = OIC Inspired (nonprofit, community services)
- Beacon College = college serving students with learning disabilities
- EA Orlando = EA Sports gaming studio in Orlando
- 811 = Sunshine 811 (call before you dig, utility safety)

---

## ADD A CONTACT

When a user asks to add a contact, follow these steps in order:

**Step 1 — Gather enough information first**
Before doing anything, make sure you know who you're adding. If the name is common or ambiguous, ask clarifying questions. At minimum you need the person's full name and outlet before proceeding. Example: "Do you know what outlet or station Joe works at?" Do not skip this step.

**Step 2 — Check Airtable first**
Search the existing contacts database for that person by name and outlet. If they already exist, tell the user and show them the existing record. Do not proceed with adding them.

**Step 3 — Gather all required fields**
Before searching for anything online, make sure you have or ask for: outlet, first name, last name, title, media type, and client(s). If any of these are missing, ask the user before proceeding. Do not add an incomplete record.

**Step 4 — Find their contact information**
Search for their email and phone in this exact order. Move to the next step only if the previous one fails:
1. Check Airtable (already done in Step 2)
2. Search the outlet's website for a staff page, team page, "Meet the Team", "Contact Us", or masthead page
3. Check their social media profiles — especially Facebook, where email is often listed in the About/Contact section. Also check Twitter/X bio and LinkedIn.
4. Search MuckRack public profiles via Google: search `"[name]" reporter site:muckrack.com`
5. Search RocketReach public profiles via Google: search `"[name]" journalist site:rocketreach.co`
6. If still not found — be honest. Tell the user you could not find the contact information. If you found a likely email format used by that outlet, suggest it to the user but DO NOT add it to the database without the user explicitly confirming it is correct. Never guess or make up an email address.

**Step 5 — Confirm before adding**
Show the user a complete summary of everything you found and ask them to confirm all details are correct before pushing anything to Airtable. Format it clearly so they can review each field.

When ready to add a contact to the database, format the data as JSON inside <add_contact> tags:
<add_contact>{"Outlet": "...", "Contact First": "...", "Contact Last": "...", "Title": "...", "Email": "...", "Phone": "...", "Media Type": "...", "Client(s)": "...", "Notes": ""}</add_contact>

---

## BUILD A MEDIA LIST

When a user asks to build a media list, follow these steps:

**Step 1 — Gather required information**
Before building anything, ask the user for any of the following that they haven't already provided:
- What is this pitch or story about?
- Which client is this for?
- What type of media are we targeting? (print, broadcast, both, trade, radio, etc.)
- What market or geography? (local, statewide, national, specific cities or regions?)
- Any specific beats or types of reporters to look for?

**Step 2 — Ask who to look for**
Ask the user: "Who should I be looking for at each outlet? For example, a features reporter, arts reporter, health reporter, editor, etc."

When researching, look specifically for that type of contact. If that type of contact does not exist at an outlet, or the person has not published anything in the past month and may no longer be active, tell the user: "I couldn't find an active [contact type] at [outlet]. Who should I look for instead?" Do not assume a fallback — always ask the user before moving on.

**Step 3 — Check Airtable first (Part 1 of the list)**
Search the existing database for contacts that match the criteria — by client tag, media type, market, and beat or title keywords. Present these to the user as Part 1: contacts already in your database.

**Step 4 — Research new contacts (Part 2 of the list)**
Go out on the web and find contacts not already in the database that fit the criteria. For each outlet or market the user specifies:
- Find the appropriate reporter or contact type based on what the user asked for
- Search the outlet's staff page, masthead, and social media
- Follow the same contact-finding process as the Add a Contact instructions
- Be transparent about where you found each contact and how confident you are in the information

**Step 5 — Handle location-based research**
When the user gives a specific location (e.g. "Aurora, Ohio"), identify:
- The largest local newspaper serving that area
- A community paper or hyperlocal publication serving that area
- Then find the right contact at each outlet using the contact type the user specified

If the user gives multiple locations, work through them one at a time unless they paste a full list, in which case confirm before starting: "I have X locations to research — this may take a few minutes. Should I proceed?"

**Step 6 — Present for review before adding anything**
Show the user both parts together:
- Part 1: Contacts already in your database (with a download button)
- Part 2: Recommended new contacts found on the web (for review only — do not add to Airtable until the user confirms)

Ask the user which new contacts they want added to Airtable before saving anything.

**Step 7 — Output**
Export the final approved list in the standard Boulder Excel format.

When returning contacts to display, format them as JSON inside <contacts> tags:
<contacts>[{"Outlet": "...", "Contact First": "...", "Contact Last": "...", "Title": "...", "Email": "...", "Media Type": "...", "Client(s)": "..."}]</contacts>

---

## LOG PITCH HISTORY

When a user mentions a pitch outcome in a conversational way — for example "Hey, it's Ryan Greene, I secured a few live broadcast hits from Lauren Margolis when I pitched her for IAAPA Expo 2025" — do the following:

1. Identify the reporter's name from the message
2. Identify the outcome (covered, passed, no response, interview secured, etc.)
3. Identify the client or campaign if mentioned
4. Identify who is logging it (their name or initials from the message)
5. Format the log entry as: "[initials] [outcome] for [client/campaign]"
   Example: "RG secured multiple live broadcast hits for IAAPA"
6. Find the reporter in the database by name
7. If found, confirm with the user: "I'll log this to Lauren Margolis's Pitch History: [date] — [entry]. Does that look right?"
8. If confirmed, call append_pitch_history to update the record
9. If the reporter is not found in the database, let the user know

Format the log to be concise — one sentence max. Use the person's initials, not their full name.

When a tag like <log_pitch_history> appears in your reasoning, extract: reporter_first, reporter_last, entry text, and record_id if known.
To trigger a pitch history update, output JSON inside <log_pitch_history> tags:
<log_pitch_history>{"record_id": "...", "entry": "...", "existing_history": "..."}</log_pitch_history>

## GENERAL RULES

- Always check Airtable before searching the web. The database is the source of truth.
- Never make up or guess contact information. If you cannot find it, say so.
- Always confirm with the user before adding or modifying anything in the database.
- Be conversational and ask clarifying questions when needed — it is better to ask than to assume.
- Keep pitch writing concise: 3 paragraphs max, lead with the news hook, reference the reporter's specific recent work, explain why it matters to their audience, end with a clear call to action. Never use words like "exciting" or "thrilled."
- When writing pitches, use web search to look up the reporter's recent articles and social media before writing.
"""

def call_claude(messages, contacts_context=""):
    api_key = st.secrets["ANTHROPIC_API_KEY"]
    system = SYSTEM_PROMPT
    if contacts_context:
        system += f"\n\n## CURRENT DATABASE\nUse this as your Airtable reference:\n{contacts_context}"

    payload = {
        "model": "claude-sonnet-4-5",
        "max_tokens": 4000,
        "system": system,
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "messages": messages
    }

    import time
    for attempt in range(3):
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json=payload,
            timeout=90
        )
        if resp.status_code == 429:
            wait = 20 * (attempt + 1)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()
    return resp.json()

def extract_text(response):
    text = ""
    for block in response.get("content", []):
        if block.get("type") == "text":
            text += block.get("text", "")
    return text

def extract_contacts_from_response(text):
    import re
    match = re.search(r'<contacts>(.*?)</contacts>', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            return None
    return None

def extract_add_contact_from_response(text):
    import re
    match = re.search(r'<add_contact>(.*?)</add_contact>', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            return None
    return None

def extract_pitch_history_from_response(text):
    import re
    match = re.search(r'<log_pitch_history>(.*?)</log_pitch_history>', text, re.DOTALL)
    if match:
        try:
            import json
            return json.loads(match.group(1))
        except:
            return None
    return None

def clean_response_text(text):
    import re
    text = re.sub(r'<contacts>.*?</contacts>', '', text, flags=re.DOTALL)
    text = re.sub(r'<add_contact>.*?</add_contact>', '', text, flags=re.DOTALL)
    text = re.sub(r'<log_pitch_history>.*?</log_pitch_history>', '', text, flags=re.DOTALL)
    return text.strip()

def build_contacts_context(contacts):
    lines = []
    for c in contacts:
        name = f"{c.get('Contact First','')} {c.get('Contact Last','')}".strip()
        pitch_history = c.get('Pitch History', '') or ''
        ph_str = f" | PITCH HISTORY: {pitch_history}" if pitch_history else ""
        lines.append(
            f"{c.get('_id','')} | {c.get('Outlet','')} | {name} | {c.get('Title','')} | "
            f"{c.get('Email','')} | {c.get('Media Type','')} | "
            f"{c.get('Client(s)','')} | {c.get('Market Type','')} | {c.get('Market','')}{ph_str}"
        )
    return "\n".join(lines)

def show():
    st.markdown("<br>", unsafe_allow_html=True)

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
        ("outlet",    "What's the reporter's outlet?"),
        ("firstName", "What's their first name?"),
        ("lastName",  "What's their last name?"),
        ("title",     "What's their title?"),
        ("email",     "What's their email? If you don't know, leave it blank."),
        ("phone",     "What's their phone number? If you don't know, leave it blank."),
        ("mediaType", "What type of media is this? (e.g. Print & Online, Broadcast (TV), Radio, Newsletter, Podcast, Trade Media)"),
        ("clients",   "Which client(s) is this contact for? Select all that apply."),
        ("notes",     "Anything else worth noting? If nothing, leave it blank."),
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
                    opener = "I'd like to build a media list."
                    st.session_state.bot_messages.append({"role": "user", "content": opener})
                    st.session_state.api_messages.append({"role": "user", "content": opener})
                    st.rerun()
            with btn_cols[1]:
                if st.button("🔍 Find a Contact", use_container_width=True):
                    opener = "I need to find a contact."
                    st.session_state.bot_messages.append({"role": "user", "content": opener})
                    st.session_state.api_messages.append({"role": "user", "content": opener})
                    st.rerun()
                if st.button("✍️ Write a Pitch", use_container_width=True):
                    opener = "I need help writing a pitch."
                    st.session_state.bot_messages.append({"role": "user", "content": opener})
                    st.session_state.api_messages.append({"role": "user", "content": opener})
                    st.rerun()

    st.markdown("---")

    # Custom styled chat display
    BOULDER_AVATAR = "https://raw.githubusercontent.com/Ryan-Greene/media-contacts-app/main/c%26pboulder.png"
    CAR_AVATAR = "https://raw.githubusercontent.com/Ryan-Greene/media-contacts-app/main/car_avatar.png"

    st.markdown("""
        <style>
            .chat-row {
                display: flex;
                align-items: flex-start;
                margin-bottom: 1.2rem;
                gap: 12px;
            }
            .chat-row.user {
                flex-direction: row-reverse;
            }
            .chat-avatar {
                width: 38px;
                height: 38px;
                border-radius: 50%;
                object-fit: cover;
                flex-shrink: 0;
                margin-top: 2px;
            }
            .chat-bubble {
                max-width: 75%;
                padding: 12px 16px;
                border-radius: 18px;
                font-family: Calibri, sans-serif;
                font-size: 15px;
                line-height: 1.5;
            }
            .chat-bubble.assistant {
                background-color: #1e1e2e;
                color: #e8e8f0;
                border-top-left-radius: 4px;
            }
            .chat-bubble.user {
                background-color: #c0392b;
                color: #ffffff;
                border-top-right-radius: 4px;
            }
            .chat-name {
                font-size: 11px;
                color: #888;
                margin-bottom: 4px;
                font-family: Calibri, sans-serif;
            }
            .chat-row.user .chat-name {
                text-align: right;
            }
        </style>
    """, unsafe_allow_html=True)

    for msg in st.session_state.bot_messages:
        role = msg["role"]
        avatar = BOULDER_AVATAR if role == "assistant" else CAR_AVATAR
        name = "Boulder" if role == "assistant" else "You"
        bubble_class = "assistant" if role == "assistant" else "user"
        row_class = "user" if role == "user" else ""

        st.markdown(f"""
            <div class="chat-row {row_class}">
                <img src="{avatar}" class="chat-avatar"/>
                <div>
                    <div class="chat-name">{name}</div>
                    <div class="chat-bubble {bubble_class}">{msg["content"]}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

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

    # Pending contact confirmation
    if st.session_state.pending_add_contact:
        pc = st.session_state.pending_add_contact
        with st.chat_message("assistant"):
            st.markdown("Here's what I found — does this look right?")
            col1, col2 = st.columns(2)
            with col1:
                pc["Contact First"] = st.text_input("First Name", value=pc.get("Contact First",""), key="pc_first")
                pc["Contact Last"]  = st.text_input("Last Name",  value=pc.get("Contact Last",""),  key="pc_last")
                pc["Title"]         = st.text_input("Title",       value=pc.get("Title",""),         key="pc_title")
                pc["Email"]         = st.text_input("Email",       value=pc.get("Email",""),         key="pc_email")
            with col2:
                pc["Outlet"]     = st.text_input("Outlet",    value=pc.get("Outlet",""),    key="pc_outlet")
                pc["Phone"]      = st.text_input("Phone",     value=pc.get("Phone",""),     key="pc_phone")
                pc["Client(s)"]  = st.text_input("Client(s)", value=pc.get("Client(s)",""), key="pc_clients")
                media_idx = MEDIA_TYPES.index(pc.get("Media Type","Print & Online")) if pc.get("Media Type") in MEDIA_TYPES else 0
                pc["Media Type"] = st.selectbox("Media Type", MEDIA_TYPES, index=media_idx, key="pc_media")
            bcol1, bcol2 = st.columns(2)
            with bcol1:
                if st.button("✅ Add to Database", type="primary", key="confirm_add"):
                    with st.spinner("Adding..."):
                        success, errors = create_contacts([pc])
                    if success:
                        name = f"{pc.get('Contact First','')} {pc.get('Contact Last','')}".strip() or pc.get('Outlet','')
                        st.session_state.bot_messages.append({
                            "role": "assistant",
                            "content": f"✅ **{name}** has been added to the database!",
                            "key": len(st.session_state.bot_messages)
                        })
                        st.session_state.pending_add_contact = None
                        st.cache_data.clear()
                        st.rerun()
            with bcol2:
                if st.button("❌ Cancel", key="cancel_add"):
                    st.session_state.pending_add_contact = None
                    st.session_state.bot_messages.append({
                        "role": "assistant",
                        "content": "No problem — contact was not added.",
                        "key": len(st.session_state.bot_messages)
                    })
                    st.rerun()

    # Guided Add Contact flow (button-triggered only)
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
                    flow["outlet"]    = st.text_input("Outlet",     value=flow.get("outlet",""),    key="cf_outlet")
                    flow["firstName"] = st.text_input("First Name", value=flow.get("firstName",""), key="cf_first")
                    flow["lastName"]  = st.text_input("Last Name",  value=flow.get("lastName",""),  key="cf_last")
                    flow["title"]     = st.text_input("Title",      value=flow.get("title",""),     key="cf_title")
                    flow["email"]     = st.text_input("Email",      value=flow.get("email",""),     key="cf_email")
                with col2:
                    flow["phone"]    = st.text_input("Phone",     value=flow.get("phone",""),    key="cf_phone")
                    flow["clients"]  = st.text_input("Client(s)", value=flow.get("clients",""),  key="cf_clients")
                    flow["notes"]    = st.text_area("Notes",      value=flow.get("notes",""),    key="cf_notes", height=80)
                    media_idx = MEDIA_TYPES.index(flow.get("mediaType","Print & Online")) if flow.get("mediaType") in MEDIA_TYPES else 0
                    flow["mediaType"] = st.selectbox("Media Type", MEDIA_TYPES, index=media_idx, key="cf_media")
                bcol1, bcol2 = st.columns(2)
                with bcol1:
                    if st.button("✅ Add to Database", type="primary", key="flow_confirm"):
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
                            st.session_state.bot_messages.append({
                                "role": "assistant",
                                "content": f"✅ **{name}** from **{flow.get('outlet','')}** has been added!",
                                "key": len(st.session_state.bot_messages)
                            })
                            st.session_state.add_flow = None
                            st.session_state.add_step = 0
                            st.cache_data.clear()
                            st.rerun()
                with bcol2:
                    if st.button("❌ Cancel", key="flow_cancel"):
                        st.session_state.bot_messages.append({"role": "assistant", "content": "No problem — contact was not added."})
                        st.session_state.add_flow = None
                        st.session_state.add_step = 0
                        st.rerun()

    # Chat input — only active when not in guided flow
    if st.session_state.add_flow is None and st.session_state.pending_add_contact is None:
        user_input = st.chat_input("Ask anything — find contacts, build lists, write pitches...")

        if user_input:
            st.session_state.bot_messages.append({"role": "user", "content": user_input})
            st.session_state.api_messages.append({"role": "user", "content": user_input})

            BOULDER_AVATAR = "https://raw.githubusercontent.com/Ryan-Greene/media-contacts-app/main/c%26pboulder.png"
            CAR_AVATAR = "https://raw.githubusercontent.com/Ryan-Greene/media-contacts-app/main/car_avatar.png"
            st.markdown(f"""
                <div class="chat-row user">
                    <img src="{CAR_AVATAR}" class="chat-avatar"/>
                    <div>
                        <div class="chat-name">You</div>
                        <div class="chat-bubble user">{user_input}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            with st.spinner("Thinking..."):
                try:
                    contacts = get_all_contacts()
                    contacts_context = build_contacts_context(contacts)
                    response = call_claude(st.session_state.api_messages, contacts_context)
                    raw_text = extract_text(response)
                    display_text = clean_response_text(raw_text)
                    extracted_contacts = extract_contacts_from_response(raw_text)
                    add_contact_data = extract_add_contact_from_response(raw_text)

                    st.session_state.api_messages.append({"role": "assistant", "content": raw_text})

                    BOULDER_AVATAR = "https://raw.githubusercontent.com/Ryan-Greene/media-contacts-app/main/c%26pboulder.png"
                    st.markdown(f"""
                        <div class="chat-row">
                            <img src="{BOULDER_AVATAR}" class="chat-avatar"/>
                            <div>
                                <div class="chat-name">Boulder</div>
                                <div class="chat-bubble assistant">{display_text}</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    if extracted_contacts:
                        COLS = ["Outlet","Contact First","Contact Last","Title","Email","Phone","Media Type","Client(s)"]
                        rows = [{c: contact.get(c,"") or "" for c in COLS} for contact in extracted_contacts]
                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=300)
                        msg_key = len(st.session_state.bot_messages)
                        excel_bytes = build_excel(extracted_contacts, "Boulder List")
                        st.download_button(
                            label="⬇️ Download as Excel",
                            data=excel_bytes,
                            file_name="boulder_list.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_{msg_key}"
                        )

                    pitch_history_data = extract_pitch_history_from_response(raw_text)
                    if add_contact_data:
                        st.session_state.pending_add_contact = add_contact_data
                    if pitch_history_data:
                        try:
                            record_id = pitch_history_data.get("record_id", "")
                            entry = pitch_history_data.get("entry", "")
                            existing = pitch_history_data.get("existing_history", "")
                            if record_id and entry:
                                append_pitch_history(record_id, entry, existing)
                                st.cache_data.clear()
                        except Exception as ph_err:
                            st.warning(f"Could not update pitch history: {ph_err}")

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
                    st.session_state.bot_messages.append({"role": "assistant", "content": error_msg, "key": len(st.session_state.bot_messages)})
                    with st.chat_message("assistant"):
                        st.markdown(error_msg)

    # Clear chat
    if st.session_state.bot_messages and not st.session_state.add_flow and not st.session_state.pending_add_contact:
        if st.button("🗑️ Clear chat", key="clear"):
            st.session_state.bot_messages = []
            st.session_state.api_messages = []
            st.rerun()
