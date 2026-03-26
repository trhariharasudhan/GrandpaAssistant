import os
import re
import shutil
import threading
import time
import tkinter as tk

try:
    import keyboard
except ImportError:
    keyboard = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    import pyperclip
except ImportError:
    pyperclip = None

import cv2
import numpy as np
import pyautogui

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
OCR_CONFIG = r"--oem 3 --psm 6"
OCR_DATA_CONFIG = r"--oem 3 --psm 6"
_region_hotkey_registered = None
_region_hotkey_handler = None
_region_hotkey_lock = threading.Lock()

if pytesseract and os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


def _ocr_ready():
    if pytesseract is None:
        return False

    configured_path = getattr(pytesseract.pytesseract, "tesseract_cmd", "")
    return bool(configured_path and os.path.exists(configured_path)) or bool(
        shutil.which("tesseract")
    )


def _copy_text_to_clipboard(text):
    if pyperclip is None:
        return False

    try:
        pyperclip.copy(text)
        return True
    except Exception:
        return False


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


def _show_region_overlay(region, duration_seconds=1.2, color="#3ddc97", border_width=3):
    left, top, width, height = region

    if width < 2 or height < 2:
        return False

    def worker():
        try:
            root = tk.Tk()
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.attributes("-alpha", 0.35)
            root.configure(bg="black")
            root.geometry(f"{width}x{height}+{left}+{top}")

            canvas = tk.Canvas(
                root,
                width=width,
                height=height,
                highlightthickness=0,
                bg="black",
            )
            canvas.pack(fill="both", expand=True)
            canvas.create_rectangle(
                border_width,
                border_width,
                max(border_width + 1, width - border_width),
                max(border_width + 1, height - border_width),
                outline=color,
                width=border_width,
            )

            root.after(max(200, int(duration_seconds * 1000)), root.destroy)
            root.mainloop()
        except Exception:
            return

    threading.Thread(target=worker, daemon=True).start()
    return True


def _show_live_region_preview(
    start_position,
    duration_seconds=3,
    color="#4cc9f0",
    border_width=3,
    update_interval_ms=40,
    stop_event=None,
):
    def worker():
        try:
            root = tk.Tk()
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.attributes("-alpha", 0.28)
            root.configure(bg="black")

            canvas = tk.Canvas(
                root,
                width=2,
                height=2,
                highlightthickness=0,
                bg="black",
            )
            canvas.pack(fill="both", expand=True)
            start_time = time.time()

            def update_box():
                if stop_event and stop_event.is_set():
                    root.destroy()
                    return

                if time.time() - start_time >= duration_seconds:
                    root.destroy()
                    return

                current_position = pyautogui.position()
                left = min(start_position.x, current_position.x)
                top = min(start_position.y, current_position.y)
                width = max(2, abs(current_position.x - start_position.x))
                height = max(2, abs(current_position.y - start_position.y))

                root.geometry(f"{width}x{height}+{left}+{top}")
                canvas.config(width=width, height=height)
                canvas.delete("all")
                canvas.create_rectangle(
                    border_width,
                    border_width,
                    max(border_width + 1, width - border_width),
                    max(border_width + 1, height - border_width),
                    outline=color,
                    width=border_width,
                )
                root.after(update_interval_ms, update_box)

            root.after(0, update_box)
            root.mainloop()
        except Exception:
            return

    threading.Thread(target=worker, daemon=True).start()
    return True


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


def get_screen_text_entries():
    if not _ocr_ready():
        return []

    img = _prepare_image()
    return _extract_line_entries(img)


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

    _show_region_overlay(region)
    img = _capture_region(region)
    lines = _extract_text_lines(img)

    if not lines:
        raw_text = pytesseract.image_to_string(img, config=OCR_CONFIG)
        return _clean_ocr_text(raw_text)

    return _clean_ocr_text("\n".join(lines))


def copy_named_screen_region_text(region_name):
    text = read_named_screen_region(region_name)
    if text in [
        "Tesseract OCR is not installed or not available in PATH.",
        "That screen region is not supported.",
        "Readable text was not clearly detected on the screen.",
    ]:
        return text

    if _copy_text_to_clipboard(text):
        return f"{region_name.title()} area text copied to clipboard."

    return "I could not copy the OCR text to the clipboard right now."


def read_selected_area_text(selection_wait_seconds=3):
    if not _ocr_ready():
        return "Tesseract OCR is not installed or not available in PATH."

    region = capture_selected_region(selection_wait_seconds=selection_wait_seconds)
    if isinstance(region, dict) and region.get("cancelled"):
        return "Selected area capture cancelled."
    if not region:
        return "Selected area was too small. Move the mouse to two different corners and try again."

    img = _capture_region(region)
    lines = _extract_text_lines(img)

    if not lines:
        raw_text = pytesseract.image_to_string(img, config=OCR_CONFIG)
        text = _clean_ocr_text(raw_text)
    else:
        text = _clean_ocr_text("\n".join(lines))

    return {
        "text": text,
        "bounds": region,
    }


def copy_selected_area_text(selection_wait_seconds=3):
    result = read_selected_area_text(selection_wait_seconds=selection_wait_seconds)

    if not isinstance(result, dict):
        return result

    text = result.get("text", "")
    if not text or text == "Readable text was not clearly detected on the screen.":
        return "Readable text was not clearly detected on the selected area."

    if _copy_text_to_clipboard(text):
        return {
            "text": text,
            "bounds": result.get("bounds"),
            "message": "Selected area text copied to clipboard.",
        }

    return "I could not copy the selected area text to the clipboard right now."


def copy_screen_text():
    text = read_screen_text()
    if text in [
        "Tesseract OCR is not installed or not available in PATH.",
        "Readable text was not clearly detected on the screen.",
    ]:
        return text

    if _copy_text_to_clipboard(text):
        return "Screen text copied to clipboard."

    return "I could not copy the screen text to the clipboard right now."


def capture_selected_region(selection_wait_seconds=3):
    start_position = pyautogui.position()
    stop_event = threading.Event()
    _show_live_region_preview(
        start_position,
        duration_seconds=selection_wait_seconds,
        stop_event=stop_event,
    )

    end_time = time.time() + selection_wait_seconds
    while time.time() < end_time:
        if keyboard and keyboard.is_pressed("esc"):
            stop_event.set()
            return {"cancelled": True}
        time.sleep(0.05)

    stop_event.set()
    end_position = pyautogui.position()

    left = min(start_position.x, end_position.x)
    top = min(start_position.y, end_position.y)
    width = abs(end_position.x - start_position.x)
    height = abs(end_position.y - start_position.y)

    if width < 20 or height < 20:
        return None

    region = (left, top, width, height)
    _show_region_overlay(region)
    return region


def capture_selected_area_with_feedback(selection_wait_seconds=3):
    result = read_selected_area_text(selection_wait_seconds=selection_wait_seconds)
    if isinstance(result, dict):
        return result
    return {"error": result}


def register_region_hotkey(callback, hotkey="ctrl+shift+o"):
    global _region_hotkey_registered, _region_hotkey_handler

    if keyboard is None or not hotkey:
        return False, "Keyboard hotkey support is not available."

    unregister_region_hotkey()

    def on_hotkey():
        if not _region_hotkey_lock.acquire(blocking=False):
            return

        def worker():
            try:
                result = capture_selected_area_with_feedback()
                callback(result)
            finally:
                _region_hotkey_lock.release()

        threading.Thread(target=worker, daemon=True).start()

    try:
        _region_hotkey_handler = keyboard.add_hotkey(hotkey, on_hotkey)
        _region_hotkey_registered = hotkey
        return True, hotkey
    except Exception:
        _region_hotkey_handler = None
        _region_hotkey_registered = None
        return False, "I could not register the OCR hotkey."


def unregister_region_hotkey():
    global _region_hotkey_registered, _region_hotkey_handler

    if keyboard is None:
        _region_hotkey_registered = None
        _region_hotkey_handler = None
        return False

    try:
        if _region_hotkey_handler is not None:
            keyboard.remove_hotkey(_region_hotkey_handler)
    except Exception:
        pass

    _region_hotkey_registered = None
    _region_hotkey_handler = None
    return True
