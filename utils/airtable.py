import requests
import streamlit as st
import time

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
    """Fetch all records from Airtable, handling pagination."""
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
    # Flatten to list of dicts with an added 'id' key
    contacts = []
    for r in records:
        c = r.get("fields", {})
        c["_id"] = r["id"]
        contacts.append(c)
    return contacts

def create_contacts(contacts: list[dict]):
    """Push a list of contact dicts to Airtable in batches of 10."""
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
    """Update a single record."""
    resp = requests.patch(
        f"{API_URL}/{record_id}",
        headers=_headers(),
        json={"fields": {k: v for k, v in fields.items() if k != "_id"}},
    )
    resp.raise_for_status()
    return resp.json()

def delete_contact(record_id: str):
    """Delete a single record."""
    resp = requests.delete(f"{API_URL}/{record_id}", headers=_headers())
    resp.raise_for_status()
    return resp.json()
