import requests
from brain.memory_engine import get_memory

# ===== GLOBAL CONVERSATION HISTORY =====
conversation_history = []

MAX_MESSAGES = 8  # last 8 exchanges only


def ask_ollama(prompt):
    """
    Send prompt to local Ollama model with conversation memory.
    Maintains limited structured history.
    """

    global conversation_history

    url = "http://localhost:11434/api/generate"

    # Add user message
    conversation_history.append({"role": "user", "content": prompt})

    # Keep memory limited
    conversation_history = conversation_history[-MAX_MESSAGES:]

    # Get stored user name
    user_name = get_memory("personal.identity.name") or "Captain"

    # Base prompt
    formatted_prompt = f"""
        You are Grandpa, a friendly AI assistant created by Captain.
        The user's name is {user_name}.

        Speak naturally and clearly.
        Give helpful answers.
        Keep responses short so they can be spoken aloud.
        """

    # Add conversation history
    for msg in conversation_history:
        if msg["role"] == "user":
            formatted_prompt += f"\nUser: {msg['content']}"
        else:
            formatted_prompt += f"\nAssistant: {msg['content']}"

    formatted_prompt += "\nAssistant:"

    payload = {
        "model": "phi3",
        "prompt": formatted_prompt,
        "stream": False,
        "options": {
            "num_predict": 120,
            "temperature": 0.5,
        },
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()

        data = response.json()
        reply = data.get("response", "No response from model.")

        # limit response length for TTS
        reply = reply.strip()
        reply = reply[:400]

    except requests.exceptions.Timeout:
        print("AI Timeout Error")
        reply = "AI is taking too long to respond."

    except requests.exceptions.ConnectionError:
        print("AI Connection Error")
        reply = "AI server is not running."

    except Exception as e:
        print("AI Error:", e)
        reply = "AI server not responding."

    # Add assistant reply to memory
    conversation_history.append({"role": "assistant", "content": reply})
    conversation_history = conversation_history[-MAX_MESSAGES:]

    return reply


def clear_memory():
    global conversation_history
    conversation_history.clear()
