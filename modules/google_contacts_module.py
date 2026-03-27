import json
import os
import re
import threading
import time
from difflib import SequenceMatcher

from brain.database import LEGACY_MEMORY_PATH
from utils.config import get_setting


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH = os.path.join(DATA_DIR, "google_token.json")
CACHE_PATH = os.path.join(DATA_DIR, "google_contacts_cache.json")
ALIAS_PATH = os.path.join(DATA_DIR, "contact_aliases.json")
META_PATH = os.path.join(DATA_DIR, "google_contacts_meta.json")
SCOPES = ["https://www.googleapis.com/auth/contacts.readonly"]
TRANSLITERATION_EQUIVALENTS = {
    "appa": ["அப்பா", "அப்பா ❤️", "அப்பா🙏"],
    "amma": ["அம்மா", "அம்மா ❤️", "அம்மா🙏"],
    "anna": ["அண்ணா"],
    "akka": ["அக்கா"],
    "thambi": ["தம்பி"],
    "thangachi": ["தங்கச்சி"],
    "thangai": ["தங்கை"],
    "paati": ["பாட்டி"],
    "patti": ["பாட்டி"],
    "thaatha": ["தாத்தா"],
    "thatha": ["தாத்தா"],
    "mama": ["மாமா"],
    "athai": ["அத்தை"],
    "chithi": ["சித்தி"],
    "chittappa": ["சித்தப்பா"],
    "periyamma": ["பெரியம்மா"],
    "periyappa": ["பெரியப்பா"],
}
DEFAULT_LIVE_REFRESH_MINUTES = 1


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


def _load_aliases():
    if not os.path.exists(ALIAS_PATH):
        return {}
    try:
        with open(ALIAS_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _save_aliases(aliases):
    _ensure_data_dir()
    with open(ALIAS_PATH, "w", encoding="utf-8") as file:
        json.dump(aliases, file, indent=4, ensure_ascii=False)


def _load_meta():
    if not os.path.exists(META_PATH):
        return {}
    try:
        with open(META_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _save_meta(meta):
    _ensure_data_dir()
    with open(META_PATH, "w", encoding="utf-8") as file:
        json.dump(meta, file, indent=4, ensure_ascii=False)


def _cache_age_seconds():
    meta = _load_meta()
    last_synced_at = float(meta.get("last_synced_at") or 0)
    if not last_synced_at:
        return None
    return max(0.0, time.time() - last_synced_at)


def _load_memory_file():
    if not os.path.exists(LEGACY_MEMORY_PATH):
        return {}
    try:
        with open(LEGACY_MEMORY_PATH, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def _save_memory_file(memory):
    with open(LEGACY_MEMORY_PATH, "w", encoding="utf-8") as file:
        json.dump(memory, file, indent=4, ensure_ascii=False)


def _get_contact_bucket(memory):
    personal = memory.setdefault("personal", {})
    return personal.setdefault("synced_google_contacts", [])


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
    _save_meta({"last_synced_at": time.time(), "contact_count": len(deduped)})
    return True, f"Google Contacts synced. I cached {len(deduped)} contacts."


def ensure_google_contacts_fresh(force=False, max_age_minutes=None):
    if not get_setting("google_contacts.live_refresh_enabled", True) and not force:
        return False, "Google Contacts live refresh disabled."

    if not os.path.exists(CREDENTIALS_PATH) or not os.path.exists(TOKEN_PATH):
        return False, "Google Contacts live refresh skipped."

    if max_age_minutes is None:
        max_age_minutes = float(
            get_setting("google_contacts.live_refresh_minutes", DEFAULT_LIVE_REFRESH_MINUTES)
        )

    cache_missing = not os.path.exists(CACHE_PATH)
    cache_age = _cache_age_seconds()
    is_stale = cache_missing or cache_age is None or cache_age >= max(0.05, max_age_minutes) * 60

    if not force and not is_stale:
        return False, "Google Contacts cache already fresh."

    try:
        return sync_google_contacts()
    except Exception:
        return False, "Google Contacts live refresh failed."


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
        prefix_bonus = 0.2 if alias.startswith(normalized_query) else 0.0
        exact_token_bonus = 0.25 if normalized_query in alias_tokens else 0.0
        score = max(similarity, token_overlap) + contains_bonus + prefix_bonus + exact_token_bonus
        best_score = max(best_score, score)
    return best_score


def _candidate_queries(contact_name):
    normalized_query = _normalize_name(contact_name)
    candidates = [normalized_query]
    for tamil_variant in TRANSLITERATION_EQUIVALENTS.get(normalized_query, []):
        normalized_variant = _normalize_name(tamil_variant)
        if normalized_variant and normalized_variant not in candidates:
            candidates.append(normalized_variant)
    return candidates


def get_google_contact_matches(contact_name, limit=3):
    ensure_google_contacts_fresh()
    contacts = _load_cache()
    if not contacts:
        return []

    aliases = _load_aliases()
    normalized_query = _normalize_name(contact_name)
    raw_query = " ".join(str(contact_name or "").strip().lower().split())
    aliased_target = aliases.get(normalized_query)
    if aliased_target:
        for contact in contacts:
            if _normalize_name(contact.get("display_name")) == _normalize_name(aliased_target):
                return [(contact, 1.0)]

    for contact in contacts:
        raw_candidates = [contact.get("display_name", "")] + list(contact.get("aliases", []))
        for candidate in raw_candidates:
            if raw_query and raw_query == " ".join(str(candidate or "").strip().lower().split()):
                return [(contact, 1.0)]

    scored = []
    queries = _candidate_queries(contact_name)
    for contact in contacts:
        best_score = 0.0
        for query in queries:
            score = _score_contact(query, contact)
            best_score = max(best_score, score)
        scored.append((contact, best_score))

    ranked = sorted(scored, key=lambda item: item[1], reverse=True)
    ranked = [item for item in ranked if item[1] >= 0.55]
    if not ranked:
        refreshed, _message = ensure_google_contacts_fresh(force=True)
        if refreshed:
            contacts = _load_cache()
            scored = []
            for contact in contacts:
                best_score = 0.0
                for query in queries:
                    score = _score_contact(query, contact)
                    best_score = max(best_score, score)
                scored.append((contact, best_score))
            ranked = sorted(scored, key=lambda item: item[1], reverse=True)
            ranked = [item for item in ranked if item[1] >= 0.55]
    return ranked[:limit]


def find_google_contact(contact_name):
    ranked = get_google_contact_matches(contact_name, limit=3)
    if not ranked:
        return None
    best_contact, best_score = ranked[0]
    if len(ranked) > 1 and best_score - ranked[1][1] < 0.12:
        return None
    return best_contact


def get_google_contact_field(contact_name, field_name):
    ranked = get_google_contact_matches(contact_name, limit=3)
    if not ranked:
        return None, None, []

    if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < 0.12:
        suggestions = [item[0].get("display_name") for item in ranked]
        return None, None, suggestions

    contact = ranked[0][0]

    normalized_field = "phone" if field_name in {"phone", "mobile", "number", "whatsapp"} else "email"
    value = contact.get(normalized_field)
    if not value:
        refreshed, _message = ensure_google_contacts_fresh(force=True)
        if refreshed:
            reranked = get_google_contact_matches(contact_name, limit=3)
            if reranked:
                contact = reranked[0][0]
                if len(reranked) > 1 and reranked[0][1] - reranked[1][1] < 0.12:
                    suggestions = [item[0].get("display_name") for item in reranked]
                    return None, None, suggestions
                value = contact.get(normalized_field)
        return None, contact.get("display_name"), []
    return value, contact.get("display_name"), []


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


def set_contact_alias(alias_text, contact_name):
    ranked = get_google_contact_matches(contact_name, limit=3)
    if not ranked:
        return False, f"I could not find a Google contact matching {contact_name}."

    if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < 0.12:
        options = " | ".join(item[0].get("display_name") for item in ranked)
        return False, f"I found multiple contacts for {contact_name}: {options}. Tell me the exact one."

    alias_key = _normalize_name(alias_text)
    if not alias_key:
        return False, "Tell me the alias name clearly."

    aliases = _load_aliases()
    resolved_name = ranked[0][0].get("display_name")
    aliases[alias_key] = resolved_name
    _save_aliases(aliases)
    return True, f"Okay, {alias_text} will now mean {resolved_name}."


def remove_contact_alias(alias_text):
    alias_key = _normalize_name(alias_text)
    aliases = _load_aliases()
    if alias_key not in aliases:
        return False, f"I do not have a saved contact alias for {alias_text}."
    del aliases[alias_key]
    _save_aliases(aliases)
    return True, f"I removed the contact alias {alias_text}."


def list_contact_aliases():
    aliases = _load_aliases()
    if not aliases:
        return "I do not have any saved contact aliases yet."
    parts = [f"{alias} -> {target}" for alias, target in sorted(aliases.items())]
    return "Saved contact aliases: " + " | ".join(parts[:20])


def merge_google_contacts_into_memory(limit=200):
    contacts = _load_cache()
    if not contacts:
        return False, "I do not have any synced Google contacts to merge yet."

    memory = _load_memory_file()
    bucket = _get_contact_bucket(memory)
    merged = 0
    seen = {
        (_normalize_name(item.get("name")), str(item.get("phone") or ""), str(item.get("email") or ""))
        for item in bucket
        if isinstance(item, dict)
    }

    for contact in contacts[:limit]:
        entry = {
            "name": contact.get("display_name"),
            "phone": contact.get("phone"),
            "email": contact.get("email"),
            "aliases": contact.get("aliases", []),
        }
        key = (
            _normalize_name(entry.get("name")),
            str(entry.get("phone") or ""),
            str(entry.get("email") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        bucket.append(entry)
        merged += 1

    _save_memory_file(memory)
    return True, f"Merged {merged} Google contacts into local memory."


def import_google_contact_to_memory(contact_name):
    ranked = get_google_contact_matches(contact_name, limit=3)
    if not ranked:
        return False, f"I could not find a synced Google contact matching {contact_name}."
    if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < 0.12:
        options = " | ".join(item[0].get("display_name") for item in ranked)
        return False, f"I found multiple contacts for {contact_name}: {options}. Tell me the exact one."

    contact = ranked[0][0]
    memory = _load_memory_file()
    bucket = _get_contact_bucket(memory)
    key = (
        _normalize_name(contact.get("display_name")),
        str(contact.get("phone") or ""),
        str(contact.get("email") or ""),
    )
    existing = {
        (_normalize_name(item.get("name")), str(item.get("phone") or ""), str(item.get("email") or ""))
        for item in bucket
        if isinstance(item, dict)
    }
    if key in existing:
        return True, f"{contact.get('display_name')} is already merged into local memory."

    bucket.append(
        {
            "name": contact.get("display_name"),
            "phone": contact.get("phone"),
            "email": contact.get("email"),
            "aliases": contact.get("aliases", []),
        }
    )
    _save_memory_file(memory)
    return True, f"Merged {contact.get('display_name')} into local memory."


def auto_refresh_google_contacts(refresh_hours=24):
    if not os.path.exists(CREDENTIALS_PATH) or not os.path.exists(TOKEN_PATH):
        return False, "Google Contacts auto refresh skipped."

    meta = _load_meta()
    last_synced_at = float(meta.get("last_synced_at") or 0)
    if last_synced_at and (time.time() - last_synced_at) < max(1, refresh_hours) * 3600:
        return False, "Google Contacts already fresh."

    try:
        return sync_google_contacts()
    except Exception:
        return False, "Google Contacts auto refresh failed."


def start_google_contacts_auto_refresh(refresh_hours=24):
    def worker():
        auto_refresh_google_contacts(refresh_hours=refresh_hours)

    threading.Thread(target=worker, daemon=True).start()
