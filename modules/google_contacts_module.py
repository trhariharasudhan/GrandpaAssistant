import json
import os
import re
from difflib import SequenceMatcher


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH = os.path.join(DATA_DIR, "google_token.json")
CACHE_PATH = os.path.join(DATA_DIR, "google_contacts_cache.json")
SCOPES = ["https://www.googleapis.com/auth/contacts.readonly"]


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _normalize_name(text):
    text = str(text or "")
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = " ".join(text.lower().split())
    return text


def _load_cache():
    if not os.path.exists(CACHE_PATH):
        return []
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _save_cache(contacts):
    _ensure_data_dir()
    with open(CACHE_PATH, "w", encoding="utf-8") as file:
        json.dump(contacts, file, indent=4, ensure_ascii=False)


def _build_contact_entry(person):
    names = person.get("names", []) or []
    phone_numbers = person.get("phoneNumbers", []) or []
    email_addresses = person.get("emailAddresses", []) or []
    nicknames = person.get("nicknames", []) or []

    display_name = ""
    aliases = []
    for item in names:
        if item.get("displayName") and not display_name:
            display_name = item["displayName"]
        for key in ["displayName", "givenName", "familyName", "unstructuredName"]:
            if item.get(key):
                aliases.append(item[key])

    for item in nicknames:
        if item.get("value"):
            aliases.append(item["value"])

    phones = []
    for item in phone_numbers:
        value = (item.get("value") or "").strip()
        if value and value not in phones:
            phones.append(value)

    emails = []
    for item in email_addresses:
        value = (item.get("value") or "").strip()
        if value and value not in emails:
            emails.append(value)

    aliases = [alias.strip() for alias in aliases if alias and alias.strip()]
    normalized_aliases = list(
        dict.fromkeys(_normalize_name(alias) for alias in aliases if _normalize_name(alias))
    )

    return {
        "display_name": display_name or (aliases[0] if aliases else "Unknown"),
        "aliases": aliases,
        "normalized_aliases": normalized_aliases,
        "phone": phones[0] if phones else None,
        "phones": phones,
        "email": emails[0] if emails else None,
        "emails": emails,
    }


def sync_google_contacts():
    if not os.path.exists(CREDENTIALS_PATH):
        return (
            False,
            "I could not find credentials.json in the project folder. "
            "Keep it in the repo root and try again.",
        )

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except Exception:
        return (
            False,
            "Google Contacts libraries are not installed yet. "
            "Install the updated requirements first.",
        )

    _ensure_data_dir()
    creds = None

    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    service = build("people", "v1", credentials=creds, cache_discovery=False)
    people = []
    page_token = None

    while True:
        response = (
            service.people()
            .connections()
            .list(
                resourceName="people/me",
                pageSize=200,
                pageToken=page_token,
                personFields="names,nicknames,emailAddresses,phoneNumbers",
            )
            .execute()
        )

        for person in response.get("connections", []):
            entry = _build_contact_entry(person)
            if entry["display_name"] != "Unknown" and (entry["phone"] or entry["email"]):
                people.append(entry)

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    deduped = []
    seen = set()
    for entry in people:
        key = (
            _normalize_name(entry.get("display_name")),
            entry.get("phone") or "",
            entry.get("email") or "",
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)

    _save_cache(deduped)
    return True, f"Google Contacts synced. I cached {len(deduped)} contacts."


def _score_contact(query, contact):
    normalized_query = _normalize_name(query)
    if not normalized_query:
        return 0.0

    best_score = 0.0
    for alias in contact.get("normalized_aliases", []):
        if alias == normalized_query:
            return 1.0
        token_overlap = 0.0
        alias_tokens = set(alias.split())
        query_tokens = set(normalized_query.split())
        if alias_tokens and query_tokens:
            token_overlap = len(alias_tokens & query_tokens) / max(len(query_tokens), 1)
        similarity = SequenceMatcher(None, normalized_query, alias).ratio()
        contains_bonus = 0.15 if normalized_query in alias or alias in normalized_query else 0.0
        score = max(similarity, token_overlap) + contains_bonus
        best_score = max(best_score, score)
    return best_score


def find_google_contact(contact_name):
    contacts = _load_cache()
    if not contacts:
        return None

    ranked = sorted(
        ((contact, _score_contact(contact_name, contact)) for contact in contacts),
        key=lambda item: item[1],
        reverse=True,
    )
    best_contact, best_score = ranked[0]
    if best_score < 0.55:
        return None
    return best_contact


def get_google_contact_field(contact_name, field_name):
    contact = find_google_contact(contact_name)
    if not contact:
        return None, None

    normalized_field = "phone" if field_name in {"phone", "mobile", "number", "whatsapp"} else "email"
    value = contact.get(normalized_field)
    if not value:
        return None, contact.get("display_name")
    return value, contact.get("display_name")


def list_google_contacts(limit=25):
    contacts = _load_cache()
    if not contacts:
        return "I do not have any synced Google contacts yet."

    names = [entry.get("display_name", "Unknown") for entry in contacts[:limit]]
    extra = len(contacts) - len(names)
    reply = "Synced Google contacts: " + " | ".join(names)
    if extra > 0:
        reply += f" | and {extra} more."
    return reply

