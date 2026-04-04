import difflib
import json
import os
import re
import subprocess

# ================= PATH SETUP =================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_FILE = os.path.join(DATA_DIR, "apps_cache.json")
START_MENU_PATHS = [
    r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
    os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs"),
]
LAUNCHABLE_EXTENSIONS = {".lnk", ".appref-ms", ".exe", ".msc"}
GENERIC_SUFFIXES = {"app", "application", "launcher", "shortcut", "classic"}


def _normalize_app_name(name):
    normalized = " ".join((name or "").lower().strip().split())
    if not normalized:
        return ""
    normalized = re.sub(r"[\[\]\(\)\{\}_]", " ", normalized)
    normalized = re.sub(r"[^a-z0-9\s\.\+\-]", " ", normalized)
    normalized = " ".join(normalized.split())
    normalized = normalized.replace("whats app", "whatsapp")
    if normalized.startswith("ms "):
        normalized = "microsoft " + normalized[3:]
    if normalized in {"vscode", "vs code"}:
        normalized = "visual studio code"
    return normalized


def _trim_generic_suffixes(name):
    tokens = [token for token in name.split() if token]
    while tokens and tokens[-1] in GENERIC_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def _add_app_entry(apps, raw_name, launcher_target):
    launcher = (launcher_target or "").strip()
    if not launcher:
        return
    canonical_name = _normalize_app_name(raw_name)
    if canonical_name:
        apps.setdefault(canonical_name, launcher)


# ================= APPLICATION SCANNING =================
def scan_installed_apps():
    apps = {}

    for folder in START_MENU_PATHS:
        if not os.path.exists(folder):
            continue
        for root, _dirs, files in os.walk(folder):
            for file in files:
                extension = os.path.splitext(file)[1].lower()
                if extension not in LAUNCHABLE_EXTENSIONS:
                    continue
                app_name = os.path.splitext(file)[0]
                launcher_path = os.path.join(root, file)
                _add_app_entry(apps, app_name, launcher_path)

    return apps


def scan_store_apps():
    apps = {}
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
        "Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Depth 3",
    ]

    try:
        output = subprocess.check_output(
            command,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        payload = json.loads(output.strip() or "[]")
    except Exception as error:
        print("Store apps scan error:", error)
        return apps

    rows = payload if isinstance(payload, list) else [payload]
    for item in rows:
        if not isinstance(item, dict):
            continue
        name = str(item.get("Name") or "").strip()
        app_id = str(item.get("AppID") or "").strip()
        if not name or not app_id:
            continue
        _add_app_entry(apps, name, app_id)

    return apps


def categorize_apps(apps_dict):
    categories = {
        "Office": [],
        "Browsers": [],
        "Developer Tools": [],
        "Media": [],
        "System Tools": [],
        "Others": [],
    }

    for app in sorted(apps_dict.keys()):
        name = app.lower()

        if any(
            word in name
            for word in [
                "word",
                "excel",
                "powerpoint",
                "outlook",
                "onenote",
                "publisher",
            ]
        ):
            categories["Office"].append(app)

        elif any(word in name for word in ["chrome", "edge", "firefox", "browser"]):
            categories["Browsers"].append(app)

        elif any(
            word in name for word in ["studio", "visual", "code", "installer", "obs"]
        ):
            categories["Developer Tools"].append(app)

        elif any(word in name for word in ["media", "player", "photos", "camera"]):
            categories["Media"].append(app)

        elif any(
            word in name
            for word in [
                "management",
                "services",
                "recorder",
                "character",
                "connection",
            ]
        ):
            categories["System Tools"].append(app)

        else:
            categories["Others"].append(app)

    return categories


# ================= CONTEXT MEMORY =================
LAST_TOPIC = None

CONVERSATION_HISTORY = []  # {"role": "user"/"assistant", "text": "..."}


def add_user_message(text):
    CONVERSATION_HISTORY.append({"role": "user", "text": text})
    if len(CONVERSATION_HISTORY) > 20:
        CONVERSATION_HISTORY.pop(0)


def add_assistant_message(text):
    CONVERSATION_HISTORY.append({"role": "assistant", "text": text})
    if len(CONVERSATION_HISTORY) > 20:
        CONVERSATION_HISTORY.pop(0)


def get_recent_context(n=5):
    context = ""
    for msg in CONVERSATION_HISTORY[-n:]:
        context += f"{msg['role'].capitalize()}: {msg['text']}\n"
    return context


# ================= CACHE FUNCTIONS =================
def load_apps_from_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if not isinstance(payload, dict):
                return None
            clean = {}
            for key, value in payload.items():
                name = _normalize_app_name(str(key or ""))
                target = str(value or "").strip()
                if name and target:
                    clean[name] = target
            return clean or None
        except Exception as e:
            print("Cache load error:", e)
            return None
    return None


def save_apps_to_cache(apps_dict):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)  # ensure data folder exists
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            normalized = {}
            for key, value in (apps_dict or {}).items():
                name = _normalize_app_name(str(key or ""))
                target = str(value or "").strip()
                if name and target:
                    normalized[name] = target
            json.dump(normalized, f, indent=4)
    except Exception as e:
        print("Cache save error:", e)


# ================= MAIN FUNCTION =================
def refresh_apps_cache():
    installed = scan_installed_apps()
    store = scan_store_apps()
    merged = {}
    merged.update(installed)
    merged.update(store)
    save_apps_to_cache(merged)
    return merged


def get_all_apps(refresh=False):
    if refresh:
        return refresh_apps_cache()

    cached_apps = load_apps_from_cache()
    if cached_apps:
        return cached_apps

    return refresh_apps_cache()


def find_best_app_match(app_name, apps_dict, cutoff=0.72):
    normalized_query = _normalize_app_name(app_name)
    if not normalized_query or not apps_dict:
        return None

    apps = {str(key): str(value) for key, value in apps_dict.items() if key and value}
    if normalized_query in apps:
        return normalized_query, apps[normalized_query], 1.0

    query_without_suffix = _trim_generic_suffixes(normalized_query)
    if query_without_suffix and query_without_suffix in apps:
        return query_without_suffix, apps[query_without_suffix], 0.99

    query_tokens = [token for token in query_without_suffix.split() if token]
    best_name = None
    best_score = 0.0

    for candidate_name in apps.keys():
        score = 0.0
        if candidate_name.startswith(normalized_query):
            score = max(score, 0.97)
        if normalized_query in candidate_name:
            score = max(score, 0.93)
        if query_tokens and all(token in candidate_name for token in query_tokens):
            score = max(score, 0.91)
        if score > best_score:
            best_name = candidate_name
            best_score = score

    if best_name and best_score >= cutoff:
        return best_name, apps[best_name], best_score

    close_matches = difflib.get_close_matches(normalized_query, list(apps.keys()), n=1, cutoff=cutoff)
    if close_matches:
        match_name = close_matches[0]
        score = difflib.SequenceMatcher(None, normalized_query, match_name).ratio()
        return match_name, apps[match_name], score

    return None
