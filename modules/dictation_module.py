import keyboard


DICTATION_ACTIVE = False

PUNCTUATION_MAP = {
    "comma": ",",
    "full stop": ".",
    "period": ".",
    "question mark": "?",
    "exclamation mark": "!",
    "colon": ":",
    "semicolon": ";",
    "open bracket": "(",
    "close bracket": ")",
    "open parentheses": "(",
    "close parentheses": ")",
    "new line": "\n",
    "newline": "\n",
    "tab space": "\t",
}


def start_dictation():
    global DICTATION_ACTIVE
    DICTATION_ACTIVE = True


def stop_dictation():
    global DICTATION_ACTIVE
    DICTATION_ACTIVE = False


def is_dictation_active():
    return DICTATION_ACTIVE


def _apply_punctuation(text):
    processed = f" {text.strip()} "

    for phrase in sorted(PUNCTUATION_MAP, key=len, reverse=True):
        replacement = PUNCTUATION_MAP[phrase]
        processed = processed.replace(f" {phrase} ", replacement)

    return processed.strip()


def handle_dictation_text(text):
    text = text.strip().lower()

    if not text:
        return False

    if text in ["backspace", "delete last", "remove last"]:
        keyboard.send("backspace")
        return True

    if text in ["enter", "press enter"]:
        keyboard.send("enter")
        return True

    if text in ["space", "give space"]:
        keyboard.write(" ")
        return True

    formatted = _apply_punctuation(text)
    if formatted:
        keyboard.write(formatted + " ", delay=0.03)
        return True

    return False
