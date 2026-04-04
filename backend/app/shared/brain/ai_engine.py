import json
import datetime
import os
import re
import time

import requests

from brain.memory_engine import get_memory
from brain.semantic_memory import get_semantic_memory_lines
from llm_client import generate_chat_reply, load_env_file
from utils.config import get_setting


CHAT_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "chat_history.json")
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
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

load_env_file(os.path.join(PROJECT_ROOT, ".env"))

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
        "Be warm, simple, and supportive in everyday English. "
        "Sound like a caring personal assistant."
    ),
    "casual": (
        "Be friendly, relaxed, and conversational in natural English. "
        "Use short sentences and a light chat tone, like a helpful friend."
    ),
    "professional": (
        "Be polished, clear, concise, and business-like. "
        "Keep a respectful professional tone."
    ),
    "funny": (
        "Be light, witty, and playful without becoming distracting. "
        "Keep replies useful and easy to understand."
    ),
}


def _memory_context_lines():
    lines = []
    remembered_items = {
        "User name": get_memory("personal.identity.name"),
        "Preferred name": get_memory("personal.assistant.preferred_name_for_user"),
        "Preferred language": get_memory("personal.assistant.preferred_response_language"),
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

    formatted_prompt = (
        "You are Odin, a personal AI assistant. The user may affectionately call you Grandpa as a grandfather nickname.\n"
        f"Current persona mode: {persona}.\n"
        f"Persona behavior: {persona_instruction}\n"
        f"The user's name is {user_name}.\n"
        "Use remembered personal details when relevant.\n"
        "Give direct, natural answers.\n"
        "Do not use pet names like sweetie, dear, buddy, or honey.\n"
        "Do not mention knowledge cutoff or model limitations unless the user explicitly asks.\n"
        "Avoid long disclaimers and avoid unnecessary follow-up questions.\n"
        "Keep spoken replies compact unless the user asks for detail.\n"
    )
    if persona == "casual":
        formatted_prompt += (
            "Keep the tone easy and human, like friendly chat. "
            "You may use light phrases like 'hey', 'cool', or 'got it' occasionally.\n"
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

    if not text:
        return "I am here." if compact else "I am here and ready."

    if any(phrase in text for phrase in ["your name", "who are you"]):
        return "My name is Odin. You can call me Grandpa."

    if any(phrase in text for phrase in ["who am i", "my name"]):
        return f"You are {preferred_name}."

    if any(phrase in text for phrase in ["time now", "what is the time", "tell me the time"]):
        return f"It is {now.strftime('%I:%M %p')}."

    if any(phrase in text for phrase in ["today date", "what is the date", "what day is it"]):
        return now.strftime("Today is %A, %d %B %Y.")

    if text in {"hi", "hello", "hey", "hey odin", "hello odin", "hey grandpa"}:
        return f"Hello {preferred_name}. I am ready."

    if "how are you" in text:
        return "I am doing well and ready to help."

    if any(phrase in text for phrase in ["what can you do", "help me", "offline help"]):
        return (
            "I can still help with local tasks, reminders, notes, contacts, OCR, code helpers, "
            "and system actions even when the local AI model is unavailable."
        )

    if compact:
        return "My local AI model is unavailable right now. I can still help with offline commands and built-in assistant features."
    return (
        "My local AI model is unavailable right now. "
        "I can still help with offline commands, reminders, contacts, notes, OCR, code helpers, and built-in assistant actions."
    )


def _local_conversation_fallback(prompt, compact=False):
    text = " ".join((prompt or "").strip().split())
    lowered = text.lower()

    if not lowered:
        return "Hey, I am here. Tell me what you want to chat about."

    if lowered in {"hi", "hello", "hey", "yo", "sup", "hola"} or lowered.startswith("hi "):
        return "Hey! I am doing good. How are you?"

    if lowered in {"ok", "okay", "kk", "hmm", "hmmm", "hmm.", "fine"}:
        return "Nice. Want to chat, ask something, or give me a task?"

    if any(token in lowered for token in ["lol", "lmao", "haha", "hehe"]):
        return "Haha nice. I am here, what next?"

    if any(token in lowered for token in ["thanks", "thank you", "thx"]):
        return "Anytime. I got you."

    if any(token in lowered for token in ["how are you", "how r u", "how you doing"]):
        return "I am doing great. Ready to help with anything."

    if lowered in {"bro", "macha", "machi", "da", "dei"}:
        return "Yes da, I am here. Sollu, what do you need?"

    if lowered.endswith("?"):
        return (
            "Good question. I will try my best with what I know right now. "
            "If you want, ask with a bit more detail and I will give a sharper answer."
        )

    if compact:
        return "Got it. I am here. Tell me what you want next."

    return (
        "Got your message. I can chat casually too. "
        "Ask me anything, or just say what you want to do and I will help."
    )


def _sanitize_reply_text(reply):
    text = " ".join(str(reply or "").split()).strip()
    if not text:
        return "I am ready to help."

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
        system_prompt = (
            "You are Odin, a practical desktop AI assistant. "
            f"Persona mode is {persona}. Persona behavior: {persona_instruction}. "
            "Give direct and useful answers in natural English. "
            "Do not mention knowledge cutoff, do not use pet names, and avoid filler lines."
        )
        if compact:
            system_prompt += " Keep replies short."
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
    system_prompt = (
        "You are Odin in full ChatGPT-style conversation mode. "
        f"Persona mode is {persona}. Persona behavior: {persona_instruction}. "
        "Reply like a natural, smart, friendly chat assistant in English. "
        "Always respond to every user message, including short casual messages. "
        "Give direct answers first, then short helpful context. "
        "Do not mention knowledge cutoff, policy, or model limitations unless asked directly. "
        "Do not use pet names."
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
        reply = _sanitize_reply_text(reply)
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

    reply = _sanitize_reply_text(reply)
    conversation_history.append({"role": "assistant", "content": reply})
    conversation_history = conversation_history[-MAX_MESSAGES:]
    save_history()
    return reply


def clear_memory():
    global conversation_history
    conversation_history.clear()
    save_history()
