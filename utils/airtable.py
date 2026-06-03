import requests
import streamlit as st
import time
from datetime import date

BASE_ID    = "app61cj6oJd2TneR6"
TABLE_NAME = "Contacts"
API_URL    = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

def _headers():
    token = st.secrets["AIRTABLE_TOKEN"]
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }

@st.cache_data(ttl=60)
def get_all_contacts():
    records = []
    params  = {"pageSize": 100}
    while True:
        resp = requests.get(API_URL, headers=_headers(), params=params)
        resp.raise_for_status()
        data = resp.json()
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
        params["offset"] = offset
    contacts = []
    for r in records:
        c = r.get("fields", {})
        c["_id"] = r["id"]
        contacts.append(c)
    return contacts

def create_contacts(contacts: list[dict]):
    batches = [contacts[i:i+10] for i in range(0, len(contacts), 10)]
    success = 0
    errors  = []
    for batch in batches:
        records = [{"fields": {k: v for k, v in c.items() if v and k != "_id"}}
                   for c in batch]
        resp = requests.post(API_URL, headers=_headers(), json={"records": records})
        if resp.status_code == 200:
            success += len(batch)
        else:
            errors.append(resp.text)
        time.sleep(0.25)
    return success, errors

def update_contact(record_id: str, fields: dict):
    resp = requests.patch(
        f"{API_URL}/{record_id}",
        headers=_headers(),
        json={"fields": {k: v for k, v in fields.items() if k != "_id"}},
    )
    resp.raise_for_status()
    return resp.json()

def delete_contact(record_id: str):
    resp = requests.delete(f"{API_URL}/{record_id}", headers=_headers())
    resp.raise_for_status()
    return resp.json()

def append_pitch_history(record_id: str, entry: str, existing_history: str = ""):
    """Append a new pitch history entry to a contact's Pitch History field."""
    today = date.today().strftime("%-m/%-d/%y")
    new_entry = f"{today} — {entry}"
    updated = existing_history.strip() + "\n" + new_entry if existing_history else new_entry
    return update_contact(record_id, {"Pitch History": updated})

def find_contact_by_name(first_name: str, last_name: str, outlet: str = ""):
    """Find a contact by name and optionally outlet."""
    contacts = get_all_contacts()
    fn = first_name.lower().strip()
    ln = last_name.lower().strip()
    matches = []
    for c in contacts:
        cfn = (c.get("Contact First") or "").lower()
        cln = (c.get("Contact Last") or "").lower()
        if cfn == fn and cln == ln:
            if outlet:
                if outlet.lower() in (c.get("Outlet") or "").lower():
                    matches.append(c)
            else:
                matches.append(c)
    return matches
