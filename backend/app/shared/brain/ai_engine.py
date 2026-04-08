import json
import datetime
import os
import re
import time

import requests

from brain.memory_engine import get_memory
from brain.semantic_memory import get_semantic_memory_lines
from cognition.hub import build_intelligence_prompt_boost
from llm_client import generate_chat_reply, load_env_file
from utils.config import get_setting
from utils.emotion import build_emotion_prompt_context, detect_emotion
from utils.mood_memory import build_mood_memory_context
from utils.paths import backend_data_path, project_path


CHAT_HISTORY_FILE = backend_data_path("chat_history.json")
PROJECT_ROOT = project_path()
MAX_MESSAGES = 20
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TIMEOUT_SECONDS = 25
UNWANTED_REPLY_PHRASES = [
    "as of my last update",
    "knowledge cuts off",
    "knowledge cutoff",
    "i don't have real-time",
    "i do not have real-time",
    "i can't provide real-time",
    "i cannot provide real-time",
    "please check trusted sources",
    "how was your day at work",
    "is there anything else you might need assistance",
]

load_env_file(project_path(".env"))

def load_history():
    if not os.path.exists(CHAT_HISTORY_FILE):
        return []
    try:
        if time.time() - os.path.getmtime(CHAT_HISTORY_FILE) > 86400:
            return []
        with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_history():
    try:
        with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(conversation_history, f, indent=4)
    except Exception:
        pass

conversation_history = load_history()

PERSONA_INSTRUCTIONS = {
    "friendly": (
        "Be warm, natural, and supportive in everyday English. "
        "Sound like a real person having a kind conversation, not a robotic assistant."
    ),
    "casual": (
        "Be friendly, relaxed, and conversational in natural English. "
        "Keep it human, easygoing, and short, like a smart friend chatting normally."
    ),
    "professional": (
        "Be polished, clear, and concise. "
        "Stay natural and respectful without sounding stiff or robotic."
    ),
    "funny": (
        "Be light, witty, and playful without overdoing it. "
        "Still sound natural and keep the reply useful."
    ),
}

INFO_REQUEST_PREFIXES = (
    "what is",
    "what are",
    "who is",
    "who was",
    "when is",
    "when was",
    "where is",
    "where was",
    "why is",
    "why are",
    "how to",
    "how do",
    "how does",
    "explain",
    "write",
    "generate",
    "create",
    "build",
    "debug",
    "fix",
    "open",
    "close",
    "set ",
    "add ",
    "delete ",
    "remove ",
    "list ",
)

HUMAN_CHAT_SIGNALS = (
    "i'm",
    "i am",
    "i feel",
    "feeling",
    "today was",
    "i had",
    "i'm bored",
    "im bored",
    "i'm sad",
    "i am sad",
    "i'm happy",
    "i am happy",
    "i'm angry",
    "i am angry",
    "frustrated",
    "upset",
    "low today",
    "lonely",
    "tired",
    "stressed",
)


def _memory_context_lines():
    lines = []
    forced_output_language = (
        str(get_setting("assistant.output_language", "english") or "english").strip().lower()
    )
    remembered_items = {
        "User name": get_memory("personal.identity.name"),
        "Preferred name": get_memory("personal.assistant.preferred_name_for_user"),
        "Preferred language": "English" if forced_output_language == "english" else get_memory("personal.assistant.preferred_response_language"),
        "Preferred tone": get_memory("personal.assistant.preferred_response_tone"),
        "Current job status": get_memory("professional.career_preferences.current_job_status"),
        "Preferred job role": get_memory("professional.career_preferences.preferred_job_role"),
        "Strongest skill": get_memory("professional.career_preferences.strongest_skill"),
        "One year goal": get_memory("professional.goal_timeline.one_year_goal"),
        "Five year goal": get_memory("professional.goal_timeline.five_year_goal"),
        "Ten year goal": get_memory("professional.goal_timeline.ten_year_goal"),
    }

    for label, value in remembered_items.items():
        if not value:
            continue
        if isinstance(value, list):
            value = ", ".join(map(str, value))
        lines.append(f"{label}: {value}")

    return lines


def _build_prompt(prompt, compact=False):
    persona = get_setting("assistant.persona", "friendly").lower()
    persona_instruction = PERSONA_INSTRUCTIONS.get(
        persona, PERSONA_INSTRUCTIONS["friendly"]
    )
    user_name = get_memory("personal.identity.name") or "Captain"
    emotion_context = build_emotion_prompt_context(prompt)
    mood_context = build_mood_memory_context()
    intelligence_context = build_intelligence_prompt_boost(prompt, context="casual", emotion=detect_emotion(prompt))

    formatted_prompt = (
        "You are Grandpa Assistant, and the user may affectionately call you Grandpa.\n"
        f"Current persona mode: {persona}.\n"
        f"Persona behavior: {persona_instruction}\n"
        f"The user's name is {user_name}.\n"
        f"{emotion_context}\n"
        f"{mood_context}\n"
        f"{intelligence_context or ''}\n"
        "Talk like a smart, friendly real person in casual conversation.\n"
        "The user may write in Tanglish or mixed Tamil-English, but you must always reply in natural English only.\n"
        "Do not reply in Tanglish, Tamil, or mixed slang unless the user explicitly asks for translation.\n"
        "Use remembered personal details when relevant.\n"
        "Keep replies short in normal chat, usually 1 or 2 sentences unless the user asks for detail.\n"
        "Use natural everyday language like hey, yeah, okay, or got it when it fits.\n"
        "Avoid robotic phrasing, bullet lists, and structured formatting in normal conversation.\n"
        "Match the user's mood: casual when casual, empathetic when sad, and slightly professional when serious.\n"
        "Give direct, natural answers.\n"
        "Do not use pet names like sweetie, dear, buddy, or honey.\n"
        "Do not mention knowledge cutoff or model limitations unless the user explicitly asks.\n"
        "Do not say you are human, but do sound human.\n"
        "Avoid long disclaimers and avoid unnecessary follow-up questions.\n"
        "Keep spoken replies compact unless the user asks for detail.\n"
        "For emotional conversation, do not give long counselor-style speeches. Use one warm line and at most one simple follow-up.\n"
        "For everyday casual chat, avoid sounding like an article, teacher, or customer support bot.\n"
    )
    if persona == "casual":
        formatted_prompt += (
            "Keep the tone easy and human, like friendly chat. "
            "You may use light phrases like 'hey', 'yeah', 'cool', or 'got it' occasionally.\n"
        )
    if compact:
        formatted_prompt += "Reply in 1 or 2 short sentences. Keep it easy to hear in voice mode.\n"

    memory_lines = _memory_context_lines()
    if memory_lines:
        formatted_prompt += "\nRemembered user context:\n"
        for line in memory_lines:
            formatted_prompt += f"- {line}\n"

    semantic_memory_lines = get_semantic_memory_lines(prompt, limit=3)
    if semantic_memory_lines:
        formatted_prompt += "\nAdditional relevant saved memory:\n"
        for line in semantic_memory_lines:
            formatted_prompt += f"- {line}\n"

    if conversation_history:
        formatted_prompt += "\nRecent conversation:\n"
        for message in conversation_history:
            role = "User" if message["role"] == "user" else "Assistant"
            formatted_prompt += f"{role}: {message['content']}\n"

    formatted_prompt += f"\nUser: {prompt}\nAssistant:"
    return formatted_prompt


def _offline_fallback_response(prompt, compact=False):
    text = " ".join((prompt or "").lower().strip().split())
    preferred_name = (
        get_memory("personal.assistant.preferred_name_for_user")
        or get_memory("personal.identity.name")
        or "Captain"
    )
    now = datetime.datetime.now()
    emotion = detect_emotion(text)

    if not text:
        return "I'm here." if compact else "I'm here and ready."

    if any(phrase in text for phrase in ["your name", "who are you"]):
        return "I'm Grandpa Assistant. You can call me Grandpa."

    if any(phrase in text for phrase in ["who am i", "my name"]):
        return f"You're {preferred_name}."

    if any(phrase in text for phrase in ["time now", "what is the time", "tell me the time"]):
        return f"It's {now.strftime('%I:%M %p')}."

    if any(phrase in text for phrase in ["today date", "what is the date", "what day is it"]):
        return now.strftime("Today is %A, %d %B %Y.")

    if text in {"hi", "hello", "hey", "hey odin", "hello odin", "hey grandpa"}:
        return f"Hey {preferred_name}. What's up?"

    if "how are you" in text:
        return "I'm doing good. What about you?"

    if emotion == "happy":
        return "That's awesome. What happened?" if compact else "That's awesome. What happened?"

    if emotion == "sad":
        return "Hey, that sounds tough. Want to talk about it?"

    if emotion == "angry":
        return "I get it. Want to tell me what's going on?"

    if any(phrase in text for phrase in ["what can you do", "help me", "offline help"]):
        return (
            "I can still help with local tasks, reminders, notes, contacts, OCR, code helpers, "
            "and system actions even if the local AI model is unavailable."
        )

    if compact:
        return "My local AI model isn't available right now, but I can still help with offline commands and built-in features."
    return (
        "My local AI model isn't available right now. "
        "I can still help with offline commands, reminders, contacts, notes, OCR, code helpers, and built-in assistant actions."
    )


def _local_conversation_fallback(prompt, compact=False):
    text = " ".join((prompt or "").strip().split())
    lowered = text.lower()
    emotion = detect_emotion(text)

    if not lowered:
        return "Hey, I'm here. What's up?"

    if lowered in {"hi", "hello", "hey", "yo", "sup", "hola"} or lowered.startswith("hi "):
        return "Hey! What's up?"

    if lowered in {"ok", "okay", "kk", "hmm", "hmmm", "hmm.", "fine"}:
        return "Alright. What's on your mind?"

    if any(token in lowered for token in ["lol", "lmao", "haha", "hehe"]):
        return "Haha, nice. What happened?"

    if any(token in lowered for token in ["thanks", "thank you", "thx"]):
        return "Yeah, anytime."

    if any(token in lowered for token in ["how are you", "how r u", "how you doing"]):
        return "Doing good. What about you?"

    if lowered in {"bro", "macha", "machi", "da", "dei"}:
        return "Yeah, I'm here. What do you need?"

    if emotion == "happy":
        return "That's awesome. What happened?"

    if emotion == "sad":
        return "Hey, that sounds rough. Want to talk about it?"

    if emotion == "angry":
        return "Yeah, I get why you're upset. Want to tell me what happened?"

    if lowered.endswith("?"):
        return "Yeah, ask it properly and I'll keep it simple."

    if compact:
        return "Got it. Tell me what you need."

    return "Got it. Tell me what's up, and I'll help."


def _sentence_chunks(text):
    return [item.strip() for item in re.split(r"(?<=[.!?])\s+", str(text or "").strip()) if item.strip()]


def _apply_human_contractions(text):
    replacements = {
        r"\bI am\b": "I'm",
        r"\bI do not\b": "I don't",
        r"\bI cannot\b": "I can't",
        r"\bI will\b": "I'll",
        r"\bIt is\b": "It's",
        r"\bThat is\b": "That's",
        r"\bDo not\b": "Don't",
        r"\bCan not\b": "Can't",
        r"\bYou are\b": "You're",
        r"\bWe are\b": "We're",
    }
    updated = str(text or "")
    for pattern, replacement in replacements.items():
        updated = re.sub(pattern, replacement, updated)
    return updated


def _looks_like_information_request(prompt):
    normalized = " ".join(str(prompt or "").lower().split())
    if not normalized:
        return False
    if normalized.endswith("?") and normalized.startswith(("what", "who", "when", "where", "why", "how")):
        return True
    return any(normalized.startswith(prefix) for prefix in INFO_REQUEST_PREFIXES)


def _is_human_chat_prompt(prompt):
    normalized = " ".join(str(prompt or "").lower().split())
    if not normalized:
        return False
    if _looks_like_information_request(normalized):
        return False
    if detect_emotion(normalized) != "neutral":
        return True
    if any(signal in normalized for signal in HUMAN_CHAT_SIGNALS):
        return True
    return len(normalized.split()) <= 14


def _wants_detailed_reply(prompt):
    normalized = " ".join(str(prompt or "").lower().split())
    return any(
        token in normalized
        for token in (
            "explain",
            "in detail",
            "details",
            "step by step",
            "full answer",
            "tell me more",
            "why",
            "how",
        )
    )


def _sanitize_reply_text(reply):
    text = " ".join(str(reply or "").split()).strip()
    if not text:
        return "I'm here if you need me."

    # Remove overly casual pet-name words.
    text = re.sub(r"\b(sweetie|sweety|honey|dear)\b", "friend", text, flags=re.IGNORECASE)

    parts = re.split(r"(?<=[.!?])\s+", text)
    filtered_parts = []
    for part in parts:
        lowered = part.lower()
        if any(marker in lowered for marker in UNWANTED_REPLY_PHRASES):
            continue
        filtered_parts.append(part)

    cleaned = " ".join(filtered_parts).strip()
    if not cleaned:
        cleaned = text

    cleaned = cleaned.lstrip(" ,.-")
    return cleaned[:600]


def _humanize_reply_for_chat(prompt, reply, compact=False):
    cleaned = _sanitize_reply_text(reply)
    if not cleaned:
        return _local_conversation_fallback(prompt, compact=compact)

    cleaned = _apply_human_contractions(cleaned)
    emotion = detect_emotion(prompt)
    prompt_is_human_chat = _is_human_chat_prompt(prompt)
    detailed = _wants_detailed_reply(prompt)
    sentences = _sentence_chunks(cleaned)

    if prompt_is_human_chat and emotion in {"sad", "angry", "happy"} and not detailed:
        if len(cleaned) > 180 or len(sentences) > 2:
            return _local_conversation_fallback(prompt, compact=True)

    if prompt_is_human_chat and not detailed and len(sentences) > 2:
        cleaned = " ".join(sentences[:2]).strip()

    lowered_cleaned = cleaned.lower()
    if prompt_is_human_chat and any(
        marker in lowered_cleaned
        for marker in (
            "ready to assist you",
            "how may i help",
            "whatever you need today",
            "please let me know",
            "i understand that you are",
        )
    ):
        return _local_conversation_fallback(prompt, compact=compact)

    cleaned = re.sub(
        r"\bCan you tell me a bit more about what's got you so upset\??",
        "Want to tell me what's going on?",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bWould you like to\b",
        "Want to",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bSometimes talking it out can help clear the air and calm things down\.?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned or _local_conversation_fallback(prompt, compact=compact)


def _provider_fallback_reply(prompt, compact=False):
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_api_key:
        return ""

    previous_provider = os.getenv("LLM_PROVIDER")
    previous_retries = os.getenv("OPENAI_MAX_RETRIES")
    previous_timeout = os.getenv("OPENAI_REQUEST_TIMEOUT_SECONDS")

    try:
        os.environ["LLM_PROVIDER"] = "openai"
        os.environ["OPENAI_MAX_RETRIES"] = "1"
        os.environ["OPENAI_REQUEST_TIMEOUT_SECONDS"] = "20"
        history = conversation_history[:-1] if conversation_history else []
        persona = get_setting("assistant.persona", "friendly").lower()
        persona_instruction = PERSONA_INSTRUCTIONS.get(persona, PERSONA_INSTRUCTIONS["friendly"])
        emotion_context = build_emotion_prompt_context(prompt)
        mood_context = build_mood_memory_context()
        system_prompt = (
            "You are Grandpa Assistant. Talk like a smart, friendly real person. "
            f"Persona mode is {persona}. Persona behavior: {persona_instruction}. "
            f"{emotion_context} "
            f"{mood_context} "
            "Reply in natural English only. Keep it short and human in normal chat, usually 1 or 2 sentences. "
            "Avoid robotic phrasing, bullet lists, pet names, filler lines, and knowledge-cutoff talk."
        )
        if compact:
            system_prompt += " Keep replies especially short."
        return (generate_chat_reply(history, prompt, system_prompt=system_prompt) or "").strip()
    except Exception:
        return ""
    finally:
        if previous_provider is None:
            os.environ.pop("LLM_PROVIDER", None)
        else:
            os.environ["LLM_PROVIDER"] = previous_provider
        if previous_retries is None:
            os.environ.pop("OPENAI_MAX_RETRIES", None)
        else:
            os.environ["OPENAI_MAX_RETRIES"] = previous_retries
        if previous_timeout is None:
            os.environ.pop("OPENAI_REQUEST_TIMEOUT_SECONDS", None)
        else:
            os.environ["OPENAI_REQUEST_TIMEOUT_SECONDS"] = previous_timeout


def _generate_chatgpt_full_reply(prompt, compact=False):
    prompt_text = str(prompt or "").strip()
    if not prompt_text:
        return ""

    history = conversation_history[:-1] if conversation_history else []
    persona = get_setting("assistant.persona", "casual").lower()
    persona_instruction = PERSONA_INSTRUCTIONS.get(persona, PERSONA_INSTRUCTIONS["casual"])
    emotion_context = build_emotion_prompt_context(prompt_text)
    mood_context = build_mood_memory_context()
    system_prompt = (
        "You are Grandpa Assistant in full conversation mode. "
        f"Persona mode is {persona}. Persona behavior: {persona_instruction}. "
        f"{emotion_context} "
        f"{mood_context} "
        "Reply like a natural, smart, friendly person in English. "
        "Always respond to every user message, including short casual messages. "
        "Keep most replies to 1 or 2 sentences unless the user asks for more. "
        "Give direct answers first, then short helpful context. "
        "Use natural language like hey, yeah, okay, or got it when it fits. "
        "Do not mention knowledge cutoff, policy, or model limitations unless asked directly. "
        "Do not use pet names or robotic assistant phrasing."
    )
    if compact:
        system_prompt += " Keep replies short and clear."

    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    previous_provider = os.getenv("LLM_PROVIDER")
    previous_retries = os.getenv("OPENAI_MAX_RETRIES")
    previous_timeout = os.getenv("OPENAI_REQUEST_TIMEOUT_SECONDS")

    try:
        if openai_api_key:
            os.environ["LLM_PROVIDER"] = "openai"
            os.environ["OPENAI_MAX_RETRIES"] = "1"
            os.environ["OPENAI_REQUEST_TIMEOUT_SECONDS"] = "20"
        return (generate_chat_reply(history, prompt_text, system_prompt=system_prompt) or "").strip()
    except Exception:
        return ""
    finally:
        if previous_provider is None:
            os.environ.pop("LLM_PROVIDER", None)
        else:
            os.environ["LLM_PROVIDER"] = previous_provider
        if previous_retries is None:
            os.environ.pop("OPENAI_MAX_RETRIES", None)
        else:
            os.environ["OPENAI_MAX_RETRIES"] = previous_retries
        if previous_timeout is None:
            os.environ.pop("OPENAI_REQUEST_TIMEOUT_SECONDS", None)
        else:
            os.environ["OPENAI_REQUEST_TIMEOUT_SECONDS"] = previous_timeout


def ask_ollama(prompt, stream_callback=None, compact=False):
    global conversation_history

    prompt_text = str(prompt or "").strip()
    normalized_prompt = " ".join(prompt_text.lower().split())
    quick_local_tokens = {
        "hi",
        "hello",
        "hey",
        "hi odin",
        "hello odin",
        "hey odin",
        "hi machi",
        "hi macha",
        "hmm",
        "hmmm",
        "ok",
        "okay",
        "summa",
    }
    if normalized_prompt in quick_local_tokens:
        reply = _sanitize_reply_text(_local_conversation_fallback(prompt_text, compact=compact))
        conversation_history.append({"role": "user", "content": prompt_text})
        conversation_history.append({"role": "assistant", "content": reply})
        conversation_history = conversation_history[-MAX_MESSAGES:]
        save_history()
        return reply

    conversation_history.append({"role": "user", "content": prompt_text or prompt})
    conversation_history = conversation_history[-MAX_MESSAGES:]
    save_history()

    chatgpt_mode_full = bool(get_setting("assistant.chatgpt_mode_full", False))
    if chatgpt_mode_full:
        reply = (
            _generate_chatgpt_full_reply(prompt_text, compact=compact)
            or _provider_fallback_reply(prompt_text, compact=compact)
            or _local_conversation_fallback(prompt_text, compact=compact)
        )
        reply = _humanize_reply_for_chat(prompt_text, reply, compact=compact)
        conversation_history.append({"role": "assistant", "content": reply})
        conversation_history = conversation_history[-MAX_MESSAGES:]
        save_history()
        return reply

    payload = {
        "model": get_setting("assistant.model", "phi3"),
        "prompt": _build_prompt(prompt, compact=compact),
        "stream": bool(stream_callback),
        "options": {
            "num_predict": 90 if compact else 180,
            "temperature": 0.6,
        },
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=OLLAMA_TIMEOUT_SECONDS,
            stream=bool(stream_callback),
        )
        response.raise_for_status()

        if stream_callback:
            chunks = []
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                data = json.loads(line)
                chunk = data.get("response", "")
                if chunk:
                    chunks.append(chunk)
                    stream_callback(chunk)
                if data.get("done"):
                    break
            reply = "".join(chunks).strip()
        else:
            data = response.json()
            reply = data.get("response", "").strip()

        reply = reply[:600] if reply else "No response from model."

    except requests.exceptions.Timeout:
        if get_setting("assistant.offline_mode_enabled", False):
            reply = _offline_fallback_response(prompt, compact=compact)
        else:
            reply = (
                _provider_fallback_reply(prompt, compact=compact)
                or _local_conversation_fallback(prompt, compact=compact)
            )
    except requests.exceptions.ConnectionError:
        if get_setting("assistant.offline_mode_enabled", False):
            reply = _offline_fallback_response(prompt, compact=compact)
        else:
            reply = (
                _provider_fallback_reply(prompt, compact=compact)
                or _local_conversation_fallback(prompt, compact=compact)
            )
    except Exception as error:
        if get_setting("assistant.offline_mode_enabled", False):
            reply = _offline_fallback_response(prompt, compact=compact)
        else:
            reply = (
                _provider_fallback_reply(prompt, compact=compact)
                or _local_conversation_fallback(prompt, compact=compact)
            )

    if not reply or reply.strip().lower() in {
        "no response from model.",
        "ai is taking too long to respond.",
        "ai server is not running.",
        "ai server not responding.",
    }:
        reply = _local_conversation_fallback(prompt, compact=compact)

    reply = _humanize_reply_for_chat(prompt_text, reply, compact=compact)
    conversation_history.append({"role": "assistant", "content": reply})
    conversation_history = conversation_history[-MAX_MESSAGES:]
    save_history()
    return reply


def clear_memory():
    global conversation_history
    conversation_history.clear()
    save_history()
