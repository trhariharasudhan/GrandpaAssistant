import os
import re
import shutil
import time

try:
    import pytesseract
except ImportError:
    pytesseract = None

import cv2
import numpy as np
import pyautogui

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
OCR_CONFIG = r"--oem 3 --psm 6"
OCR_DATA_CONFIG = r"--oem 3 --psm 6"

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
    return _prepare_image_array(img)


def _prepare_image_array(img):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Improve OCR quality for small UI text.
    enlarged = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    denoised = cv2.GaussianBlur(enlarged, (3, 3), 0)
    _, thresholded = cv2.threshold(
        denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return thresholded


def _capture_region(region):
    screenshot = pyautogui.screenshot(region=region)
    img = np.array(screenshot)
    return _prepare_image_array(img)


def _clean_line(line):
    line = re.sub(r"\s+", " ", line).strip()
    line = re.sub(r"[|`~_=*<>]+", " ", line)
    line = re.sub(r"^[^A-Za-z0-9]+|[^A-Za-z0-9]+$", "", line)
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


def _extract_text_lines(img):
    data = pytesseract.image_to_data(
        img, output_type=pytesseract.Output.DICT, config=OCR_DATA_CONFIG
    )

    grouped_lines = {}
    total_items = len(data["text"])

    for index in range(total_items):
        raw_text = data["text"][index]
        cleaned = _clean_line(raw_text)
        if not cleaned:
            continue

        try:
            confidence = float(data["conf"][index])
        except (TypeError, ValueError):
            confidence = -1

        if confidence < 25:
            continue

        line_key = (data["block_num"][index], data["par_num"][index], data["line_num"][index])
        grouped_lines.setdefault(line_key, []).append(
            (data["left"][index], cleaned)
        )

    ordered_lines = []
    for key in sorted(grouped_lines):
        words = [word for _, word in sorted(grouped_lines[key], key=lambda item: item[0])]
        line = _clean_line(" ".join(words))
        if line:
            ordered_lines.append(line)

    return ordered_lines


def _extract_line_entries(img):
    data = pytesseract.image_to_data(
        img, output_type=pytesseract.Output.DICT, config=OCR_DATA_CONFIG
    )

    grouped_lines = {}
    total_items = len(data["text"])

    for index in range(total_items):
        raw_text = data["text"][index]
        cleaned = _clean_line(raw_text)
        if not cleaned:
            continue

        try:
            confidence = float(data["conf"][index])
        except (TypeError, ValueError):
            confidence = -1

        if confidence < 20:
            continue

        line_key = (data["block_num"][index], data["par_num"][index], data["line_num"][index])
        grouped_lines.setdefault(line_key, []).append(
            {
                "left": data["left"][index],
                "top": data["top"][index],
                "width": data["width"][index],
                "height": data["height"][index],
                "text": cleaned,
                "confidence": confidence,
            }
        )

    entries = []
    for key in sorted(grouped_lines):
        words = sorted(grouped_lines[key], key=lambda item: item["left"])
        line_text = _clean_line(" ".join(word["text"] for word in words))
        if not line_text:
            continue

        left = min(word["left"] for word in words)
        top = min(word["top"] for word in words)
        right = max(word["left"] + word["width"] for word in words)
        bottom = max(word["top"] + word["height"] for word in words)
        avg_confidence = sum(word["confidence"] for word in words) / max(len(words), 1)

        entries.append(
            {
                "text": line_text,
                "center": ((left + right) // 2, (top + bottom) // 2),
                "bounds": (left, top, right - left, bottom - top),
                "confidence": avg_confidence,
            }
        )

    return entries


def _score_entry(entry, normalized_target, target_words):
    line_text = entry["text"].lower()
    if not line_text:
        return 0

    score = 0
    if line_text == normalized_target:
        score += 8
    if normalized_target in line_text:
        score += 5

    word_hits = sum(1 for target_word in target_words if target_word in line_text)
    score += word_hits * 2

    if target_words:
        overlap_ratio = word_hits / len(target_words)
        if overlap_ratio >= 0.8:
            score += 3
        elif overlap_ratio >= 0.5:
            score += 1

    score += min(2.0, entry["confidence"] / 50.0)
    return score


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
    details = find_text_details(target_text)
    return details["center"] if details else None


def find_text_details(target_text):
    if not _ocr_ready():
        return None

    img = _prepare_image()
    entries = _extract_line_entries(img)
    normalized_target = _clean_line(target_text).lower()
    target_words = [word for word in re.split(r"\s+", normalized_target) if word]
    best_match = None

    for entry in entries:
        score = _score_entry(entry, normalized_target, target_words)
        if score <= 0:
            continue

        candidate = {
            "text": entry["text"],
            "center": entry["center"],
            "bounds": entry["bounds"],
            "score": score,
            "confidence": entry["confidence"],
        }

        if best_match is None or candidate["score"] > best_match["score"]:
            best_match = candidate

    return best_match


def find_text_details_in_region(target_text, region):
    if not _ocr_ready():
        return None

    img = _capture_region(region)
    entries = _extract_line_entries(img)
    normalized_target = _clean_line(target_text).lower()
    target_words = [word for word in re.split(r"\s+", normalized_target) if word]
    best_match = None

    for entry in entries:
        score = _score_entry(entry, normalized_target, target_words)
        if score <= 0:
            continue

        local_x, local_y = entry["center"]
        left, top = region[0], region[1]
        candidate = {
            "text": entry["text"],
            "center": (left + local_x, top + local_y),
            "bounds": (
                left + entry["bounds"][0],
                top + entry["bounds"][1],
                entry["bounds"][2],
                entry["bounds"][3],
            ),
            "score": score,
            "confidence": entry["confidence"],
        }

        if best_match is None or candidate["score"] > best_match["score"]:
            best_match = candidate

    return best_match


def click_on_text(target):
    details = find_text_details(target)

    if details and details["score"] >= 4:
        pyautogui.click(details["center"])
        return True

    return False


def click_on_text_in_region(target, region):
    details = find_text_details_in_region(target, region)

    if details and details["score"] >= 4:
        pyautogui.click(details["center"])
        return details

    return None


def is_text_visible(target):
    return find_text_details(target) is not None


def read_screen_text():
    if not _ocr_ready():
        return "Tesseract OCR is not installed or not available in PATH."

    img = _prepare_image()
    lines = _extract_text_lines(img)

    if not lines:
        raw_text = pytesseract.image_to_string(img, config=OCR_CONFIG)
        return _clean_ocr_text(raw_text)

    return _clean_ocr_text("\n".join(lines))


def _region_from_name(region_name):
    screen_width, screen_height = pyautogui.size()
    half_width = screen_width // 2
    half_height = screen_height // 2
    quarter_width = screen_width // 4
    quarter_height = screen_height // 4

    regions = {
        "top left": (0, 0, half_width, half_height),
        "top right": (half_width, 0, screen_width - half_width, half_height),
        "bottom left": (0, half_height, half_width, screen_height - half_height),
        "bottom right": (
            half_width,
            half_height,
            screen_width - half_width,
            screen_height - half_height,
        ),
        "center": (
            quarter_width,
            quarter_height,
            half_width,
            half_height,
        ),
    }
    return regions.get(region_name)


def read_named_screen_region(region_name):
    if not _ocr_ready():
        return "Tesseract OCR is not installed or not available in PATH."

    region = _region_from_name(region_name)
    if not region:
        return "That screen region is not supported."

    img = _capture_region(region)
    lines = _extract_text_lines(img)

    if not lines:
        raw_text = pytesseract.image_to_string(img, config=OCR_CONFIG)
        return _clean_ocr_text(raw_text)

    return _clean_ocr_text("\n".join(lines))


def read_selected_area_text(selection_wait_seconds=3):
    if not _ocr_ready():
        return "Tesseract OCR is not installed or not available in PATH."

    start_position = pyautogui.position()
    time.sleep(selection_wait_seconds)
    end_position = pyautogui.position()

    left = min(start_position.x, end_position.x)
    top = min(start_position.y, end_position.y)
    width = abs(end_position.x - start_position.x)
    height = abs(end_position.y - start_position.y)

    if width < 20 or height < 20:
        return "Selected area was too small. Move the mouse to two different corners and try again."

    img = _capture_region((left, top, width, height))
    lines = _extract_text_lines(img)

    if not lines:
        raw_text = pytesseract.image_to_string(img, config=OCR_CONFIG)
        text = _clean_ocr_text(raw_text)
    else:
        text = _clean_ocr_text("\n".join(lines))

    return {
        "text": text,
        "bounds": (left, top, width, height),
    }


def capture_selected_region(selection_wait_seconds=3):
    start_position = pyautogui.position()
    time.sleep(selection_wait_seconds)
    end_position = pyautogui.position()

    left = min(start_position.x, end_position.x)
    top = min(start_position.y, end_position.y)
    width = abs(end_position.x - start_position.x)
    height = abs(end_position.y - start_position.y)

    if width < 20 or height < 20:
        return None

    return (left, top, width, height)
