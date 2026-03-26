import json

import requests

from brain.memory_engine import get_memory
from utils.config import get_setting


conversation_history = []
MAX_MESSAGES = 12
OLLAMA_URL = "http://localhost:11434/api/generate"

PERSONA_INSTRUCTIONS = {
    "friendly": (
        "Be warm, casual, encouraging, and supportive. "
        "Sound like a caring personal assistant."
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


def _build_prompt(prompt):
    persona = get_setting("assistant.persona", "friendly").lower()
    persona_instruction = PERSONA_INSTRUCTIONS.get(
        persona, PERSONA_INSTRUCTIONS["friendly"]
    )
    user_name = get_memory("personal.identity.name") or "Captain"

    formatted_prompt = (
        "You are Grandpa, a personal AI assistant.\n"
        f"Current persona mode: {persona}.\n"
        f"Persona behavior: {persona_instruction}\n"
        f"The user's name is {user_name}.\n"
        "Use remembered personal details when relevant.\n"
        "Give direct, natural answers.\n"
        "Keep spoken replies compact unless the user asks for detail.\n"
    )

    memory_lines = _memory_context_lines()
    if memory_lines:
        formatted_prompt += "\nRemembered user context:\n"
        for line in memory_lines:
            formatted_prompt += f"- {line}\n"

    if conversation_history:
        formatted_prompt += "\nRecent conversation:\n"
        for message in conversation_history:
            role = "User" if message["role"] == "user" else "Assistant"
            formatted_prompt += f"{role}: {message['content']}\n"

    formatted_prompt += f"\nUser: {prompt}\nAssistant:"
    return formatted_prompt


def ask_ollama(prompt, stream_callback=None):
    global conversation_history

    conversation_history.append({"role": "user", "content": prompt})
    conversation_history = conversation_history[-MAX_MESSAGES:]

    payload = {
        "model": get_setting("assistant.model", "phi3"),
        "prompt": _build_prompt(prompt),
        "stream": bool(stream_callback),
        "options": {
            "num_predict": 180,
            "temperature": 0.6,
        },
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=90,
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
        print("AI Timeout Error")
        reply = "AI is taking too long to respond."
    except requests.exceptions.ConnectionError:
        print("AI Connection Error")
        reply = "AI server is not running."
    except Exception as error:
        print("AI Error:", error)
        reply = "AI server not responding."

    conversation_history.append({"role": "assistant", "content": reply})
    conversation_history = conversation_history[-MAX_MESSAGES:]
    return reply


def clear_memory():
    global conversation_history
    conversation_history.clear()
