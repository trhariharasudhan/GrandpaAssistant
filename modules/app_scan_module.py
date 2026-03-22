import json
import os
import subprocess

# ================= PATH SETUP =================
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_FILE = os.path.join(DATA_DIR, "apps_cache.json")


# ================= APPLICATION SCANNING =================
def scan_installed_apps():
    apps = {}
    start_menu_paths = [
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs"),
    ]

    for folder in start_menu_paths:
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.endswith(".lnk"):
                    app_name = os.path.splitext(file)[0].lower()
                    apps[app_name] = os.path.join(root, file)

    return apps


def scan_store_apps():
    apps = {}

    try:
        output = subprocess.check_output(
            'powershell "Get-StartApps | Select Name, AppID"', shell=True
        ).decode(errors="ignore")

        lines = output.splitlines()[3:]  # skip header lines

        for line in lines:
            if line.strip():
                parts = line.strip().split()
                if len(parts) >= 2:
                    name = " ".join(parts[:-1]).lower()
                    appid = parts[-1]
                    apps[name] = appid

    except Exception as e:
        print("Store apps scan error:", e)

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
                return json.load(f)
        except Exception as e:
            print("Cache load error:", e)
            return None
    return None


def save_apps_to_cache(apps_dict):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)  # ensure data folder exists
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(apps_dict, f, indent=4)
    except Exception as e:
        print("Cache save error:", e)


# ================= MAIN FUNCTION =================
def get_all_apps():
    # Try loading from cache
    cached_apps = load_apps_from_cache()

    if cached_apps:
        return cached_apps

    # If no cache, scan the system.
    installed = scan_installed_apps()
    store = scan_store_apps()
    installed.update(store)

    save_apps_to_cache(installed)

    return installed
