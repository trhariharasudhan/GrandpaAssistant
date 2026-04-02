from duckduckgo_search import DDGS
import wikipediaapi

from brain.ai_engine import ask_ollama
import system.app_scan_module as app_scan_module

ANSWER_MODE = "short"


def web_fallback(query):
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=3)
            combined_text = ""
            for result in results:
                combined_text += result["title"] + "\n"
                combined_text += result["body"] + "\n\n"

        return ask_ollama(f"Summarize this information clearly:\n{combined_text}")
    except Exception:
        return "I couldn't retrieve information from the web."


def wikipedia_search(command):
    global ANSWER_MODE

    try:
        command = command.lower().replace("?", "").strip()

        if "long answer" in command:
            ANSWER_MODE = "long"
            return "Switched to long answer mode."

        if "short answer" in command:
            ANSWER_MODE = "short"
            return "Switched to short answer mode."

        for phrase in ["who is", "what is", "tell me about"]:
            if command.startswith(phrase):
                command = command.replace(phrase, "", 1).strip()

        if not command:
            return "Please tell me what to search."

        wiki = wikipediaapi.Wikipedia(language="en", user_agent="GrandpaAssistant/1.0")
        page = wiki.page(command)

        if page.exists():
            app_scan_module.LAST_TOPIC = command
            return page.summary[:500] if ANSWER_MODE == "short" else page.summary[:1500]

        ai_response = ask_ollama(f"Explain about {command} in simple terms.")
        if ai_response and len(ai_response) >= 80:
            app_scan_module.LAST_TOPIC = command
            return ai_response

        web_response = web_fallback(command)
        app_scan_module.LAST_TOPIC = command
        return web_response

    except Exception:
        ai_response = ask_ollama(f"Explain about {command} in simple terms.")
        if ai_response and len(ai_response) >= 80:
            app_scan_module.LAST_TOPIC = command
            return ai_response

        web_response = web_fallback(command)
        app_scan_module.LAST_TOPIC = command
        return web_response
