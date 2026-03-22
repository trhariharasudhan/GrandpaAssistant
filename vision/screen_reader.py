import os
import re
import shutil

try:
    import pytesseract
except ImportError:
    pytesseract = None

import cv2
import numpy as np
import pyautogui

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
OCR_CONFIG = r"--oem 3 --psm 6"

if pytesseract and os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


def _ocr_ready():
    if pytesseract is None:
        return False

    configured_path = getattr(pytesseract.pytesseract, "tesseract_cmd", "")
    return bool(configured_path and os.path.exists(configured_path)) or bool(
        shutil.which("tesseract")
    )


def _prepare_image():
    screenshot = pyautogui.screenshot()
    img = np.array(screenshot)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Improve OCR quality for small UI text.
    enlarged = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    denoised = cv2.GaussianBlur(enlarged, (3, 3), 0)
    _, thresholded = cv2.threshold(
        denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return thresholded


def _clean_line(line):
    line = re.sub(r"\s+", " ", line).strip()
    line = re.sub(r"[|`~_=*<>]+", " ", line)
    line = re.sub(r"\s+", " ", line).strip()
    return line


def _is_useful_line(line):
    if not line:
        return False

    if len(line) <= 1:
        return False

    alpha_count = sum(char.isalpha() for char in line)
    digit_count = sum(char.isdigit() for char in line)
    useful_chars = alpha_count + digit_count

    if useful_chars < 2:
        return False

    if len(line) <= 3 and alpha_count < 2:
        return False

    # Reject mostly-symbol noise like OCR garbage headers.
    if useful_chars / max(len(line), 1) < 0.45:
        return False

    return True


def _clean_ocr_text(text):
    cleaned_lines = []
    seen = set()

    for raw_line in text.splitlines():
        line = _clean_line(raw_line)

        if not _is_useful_line(line):
            continue

        lowered = line.lower()
        if lowered in seen:
            continue

        seen.add(lowered)
        cleaned_lines.append(line)

    if not cleaned_lines:
        return "Readable text was not clearly detected on the screen."

    return "\n".join(cleaned_lines)


def find_text_on_screen(target_text):
    if not _ocr_ready():
        return None

    img = _prepare_image()
    data = pytesseract.image_to_data(
        img, output_type=pytesseract.Output.DICT, config=OCR_CONFIG
    )

    for index, word in enumerate(data["text"]):
        if target_text.lower() in word.lower():
            x = data["left"][index]
            y = data["top"][index]
            width = data["width"][index]
            height = data["height"][index]
            return x + width // 2, y + height // 2

    return None


def click_on_text(target):
    position = find_text_on_screen(target)

    if position:
        pyautogui.click(position)
        return True

    return False


def read_screen_text():
    if not _ocr_ready():
        return "Tesseract OCR is not installed or not available in PATH."

    img = _prepare_image()
    raw_text = pytesseract.image_to_string(img, config=OCR_CONFIG)
    return _clean_ocr_text(raw_text)
