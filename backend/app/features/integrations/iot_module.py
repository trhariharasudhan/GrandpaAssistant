import json
import os
import requests
from contextlib import suppress

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "data", "iot_credentials.json")

def _load_iot_credentials():
    if not os.path.exists(CREDENTIALS_PATH):
        return None
    try:
        with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def dispatch_iot_command(command_text):
    """
    Attempts to match the user's spoken string directly against the keys in 'webhooks'.
    If a match is found, it fires the HTTP request.
    Example: command_text = "turn on bedroom light"
    """
    creds = _load_iot_credentials()
    if not creds:
        return False, "IoT config file is missing."

    if not creds.get("enabled"):
        return False, "Smart Home controls are currently disabled in settings."

    webhooks = creds.get("webhooks", {})
    if not webhooks:
        return False, "No Smart Home devices are configured."

    # Normalize command
    normalized = " ".join(command_text.lower().strip().split())

    if normalized not in webhooks:
        return False, f"I couldn't find a Smart Home device matching that exact command. Try something like '{list(webhooks.keys())[0]}' if configured."

    config = webhooks[normalized]
    url = config.get("url")
    method = config.get("method", "POST").upper()
    success_msg = config.get("success_message", "Done.")

    if not url or "YOUR_KEY_HERE" in url or "YOUR_HOME_ASSISTANT_WEBHOOK_ID" in url:
        return False, "This device is set up in your config, but you haven't entered the real API key yet."

    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        else:
            response = requests.post(url, timeout=5)
            
        if response.status_code in [200, 201, 202, 204]:
            return True, success_msg
        else:
            return False, f"The Smart Home hub returned an error: status code {response.status_code}."
    except requests.exceptions.RequestException as e:
        return False, f"I couldn't reach your Smart Home hub. Please check your network. ({str(e)})"
