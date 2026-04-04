import re
from urllib.parse import quote

try:
    from duckduckgo_search import DDGS
    DDGS_IMPORT_ERROR = ""
except Exception as import_error:
    DDGS = None
    DDGS_IMPORT_ERROR = str(import_error)

import wikipediaapi
import requests

from brain.ai_engine import ask_ollama
import system.app_scan_module as app_scan_module

ANSWER_MODE = "short"
KNOWN_PROFILE_FALLBACKS = {
    "madan gowri": (
        "Madan Gowri is a Tamil content creator and YouTuber known for explanatory videos, "
        "social topic breakdowns, and interview-style content."
    ),
}


def _extract_search_topic(command):
    text = (command or "").lower().replace("?", "").strip()
    if not text:
        return ""

    prefixes = [
        "who is",
        "who was",
        "what is",
        "what are",
        "tell me about",
        "how is",
        "how are",
        "latest about",
        "latest on",
        "news about",
        "about",
    ]
    for prefix in prefixes:
        if text.startswith(prefix + " "):
            text = text[len(prefix):].strip()
            break

    text = re.sub(r"^(the|a|an)\s+", "", text).strip()
    return text


def _trim_summary(text, limit):
    clean = " ".join((text or "").split()).strip()
    if len(clean) <= limit:
        return clean

    clipped = clean[:limit].rstrip()
    for marker in [". ", "! ", "? "]:
        idx = clipped.rfind(marker)
        if idx >= int(limit * 0.55):
            return clipped[: idx + 1].strip()

    if " " in clipped:
        return clipped.rsplit(" ", 1)[0].strip() + "..."
    return clipped + "..."


def _strip_html_tags(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _best_wikipedia_search_item(items, query):
    query_tokens = [token for token in re.findall(r"[a-z0-9]+", query.lower()) if token]
    if not items:
        return None

    def _score(item):
        title = str(item.get("title") or "").lower()
        snippet = _strip_html_tags(str(item.get("snippet") or "")).lower()
        combined = f"{title} {snippet}"
        token_hits = sum(1 for token in query_tokens if token in combined)
        exact_phrase = 2 if query.lower() in combined else 0
        return token_hits + exact_phrase

    ranked = sorted(items, key=_score, reverse=True)
    return ranked[0] if ranked else None


def _wikipedia_search_api_summary(topic):
    query = (topic or "").strip()
    if not query:
        return ""

    try:
        query_tokens = [token for token in re.findall(r"[a-z0-9]+", query.lower()) if token]
        headers = {
            "User-Agent": "GrandpaAssistant/1.0 (local desktop assistant)",
        }
        search_items = []
        seen_titles = set()
        search_queries = [f'intitle:"{query}"', f'"{query}"', query]

        for search_query in search_queries:
            search_response = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": search_query,
                    "utf8": 1,
                    "format": "json",
                    "srlimit": 5,
                },
                headers=headers,
                timeout=7,
            )
            search_response.raise_for_status()
            search_payload = search_response.json() or {}
            items = (
                search_payload.get("query", {}).get("search", [])
                if isinstance(search_payload, dict)
                else []
            )
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or "").strip()
                title_key = title.lower()
                if not title or title_key in seen_titles:
                    continue
                seen_titles.add(title_key)
                search_items.append(item)
            if search_items:
                break

        best_item = _best_wikipedia_search_item(search_items, query)
        if not best_item:
            return ""

        title = str(best_item.get("title") or "").strip()
        snippet = _strip_html_tags(str(best_item.get("snippet") or "").strip())
        if not title:
            return snippet

        lower_title = title.lower()
        title_token_hits = sum(1 for token in query_tokens if token in lower_title)
        exact_title_match = query.lower() in lower_title
        strong_match = exact_title_match or (
            len(query_tokens) > 0 and title_token_hits >= max(2, len(query_tokens))
        )

        if not strong_match:
            if snippet and query.lower() in snippet.lower():
                short_snippet = _trim_summary(snippet, 180)
                return (
                    f"I could not find an exact Wikipedia page for {query.title()}. "
                    f"Closest mention: {short_snippet}"
                )
            return ""

        summary_response = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title.replace(' ', '_'))}",
            headers=headers,
            timeout=7,
        )
        if summary_response.ok:
            payload = summary_response.json() or {}
            extract = " ".join(str(payload.get("extract") or "").split()).strip()
            if extract:
                return extract

        if snippet:
            return f"{title}: {snippet}"
        return title
    except Exception:
        return ""


def web_fallback(query):
    if DDGS is None:
        if DDGS_IMPORT_ERROR:
            return (
                "Web search is currently unavailable on this system "
                f"({DDGS_IMPORT_ERROR})."
            )
        return "Web search is currently unavailable on this system."

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

    topic = ""
    try:
        command = command.lower().replace("?", "").strip()

        if "long answer" in command:
            ANSWER_MODE = "long"
            return "Switched to long answer mode."

        if "short answer" in command:
            ANSWER_MODE = "short"
            return "Switched to short answer mode."

        topic = _extract_search_topic(command)
        if not topic:
            return "Please tell me what to search."

        if topic in KNOWN_PROFILE_FALLBACKS:
            app_scan_module.LAST_TOPIC = topic
            return KNOWN_PROFILE_FALLBACKS[topic]

        wiki = wikipediaapi.Wikipedia(language="en", user_agent="GrandpaAssistant/1.0")
        candidates = [topic, topic.title()]
        for candidate in candidates:
            page = wiki.page(candidate)
            if not page.exists():
                continue
            summary = (page.summary or "").strip()
            if not summary:
                continue
            if "may refer to:" in summary.lower():
                app_scan_module.LAST_TOPIC = topic
                if topic == "marvel":
                    return (
                        "Marvel commonly refers to the entertainment brand behind Marvel Comics "
                        "and Marvel Studios."
                    )
                return (
                    f"{topic.title()} has multiple meanings. "
                    f"The most common use is the main topic named {topic.title()}."
                )
            app_scan_module.LAST_TOPIC = topic
            return (
                _trim_summary(summary, 500)
                if ANSWER_MODE == "short"
                else _trim_summary(summary, 1500)
            )

        api_summary = _wikipedia_search_api_summary(topic)
        if api_summary:
            app_scan_module.LAST_TOPIC = topic
            return (
                _trim_summary(api_summary, 500)
                if ANSWER_MODE == "short"
                else _trim_summary(api_summary, 1500)
            )

        web_response = web_fallback(topic)
        if web_response and "unavailable on this system" not in web_response.lower():
            app_scan_module.LAST_TOPIC = topic
            return web_response

        ai_response = ask_ollama(f"Explain about {topic} in simple terms.")
        if ai_response:
            app_scan_module.LAST_TOPIC = topic
            return ai_response

        app_scan_module.LAST_TOPIC = topic
        return web_response or "I could not find a clear answer right now."

    except Exception:
        safe_topic = topic or _extract_search_topic(command)
        api_summary = _wikipedia_search_api_summary(safe_topic)
        if api_summary:
            app_scan_module.LAST_TOPIC = safe_topic
            return (
                _trim_summary(api_summary, 500)
                if ANSWER_MODE == "short"
                else _trim_summary(api_summary, 1500)
            )

        ai_response = ask_ollama(f"Explain about {safe_topic} in simple terms.")
        if ai_response:
            app_scan_module.LAST_TOPIC = safe_topic
            return ai_response

        web_response = web_fallback(safe_topic)
        app_scan_module.LAST_TOPIC = safe_topic
        return web_response
