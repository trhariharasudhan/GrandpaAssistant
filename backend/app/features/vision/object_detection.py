import os
import threading
import time
from collections import Counter

import cv2
import numpy as np
import pyautogui

from utils.config import get_setting, update_setting


def _prepare_ultralytics_config_dir():
    if os.getenv("YOLO_CONFIG_DIR"):
        return
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    config_root = os.path.join(backend_root, "data", "runtime")
    ultralytics_root = os.path.join(config_root, "ultralytics")
    os.makedirs(ultralytics_root, exist_ok=True)
    os.environ["YOLO_CONFIG_DIR"] = config_root


_prepare_ultralytics_config_dir()

try:
    from ultralytics import YOLO
    _IMPORT_ERROR = None
except Exception as error:
    YOLO = None
    _IMPORT_ERROR = str(error)


_MODEL = None
_STATE_LOCK = threading.Lock()
_LATEST_LABELS = []
_LATEST_UPDATED_AT = 0.0
_WATCH_TARGET = ""
_WATCH_LAST_SEEN_AT = 0.0
_WATCH_LAST_ALERT_AT = 0.0
_DETECTION_HISTORY = []
_WATCH_EVENT_HISTORY = []


def _append_history(target_list, item, limit=20):
    target_list.append(item)
    if len(target_list) > limit:
        del target_list[:-limit]


def _extract_labels(result, confidence_threshold):
    labels = []
    boxes = getattr(result, "boxes", None)
    names = getattr(result, "names", {})
    if boxes is not None:
        for box in boxes:
            confidence = float(box.conf[0].item())
            if confidence < confidence_threshold:
                continue
            cls_index = int(box.cls[0].item())
            labels.append(str(names.get(cls_index, f"class {cls_index}")))
    return labels


def _set_latest_labels(labels):
    global _LATEST_LABELS, _LATEST_UPDATED_AT, _WATCH_LAST_SEEN_AT
    with _STATE_LOCK:
        _LATEST_LABELS = list(labels)
        _LATEST_UPDATED_AT = time.time()
        if labels:
            _append_history(
                _DETECTION_HISTORY,
                {
                    "timestamp": _LATEST_UPDATED_AT,
                    "labels": list(labels),
                    "summary": _labels_to_summary(labels),
                },
            )
        if _WATCH_TARGET and any(label.lower() == _WATCH_TARGET for label in labels):
            _WATCH_LAST_SEEN_AT = _LATEST_UPDATED_AT


def _object_settings():
    return {
        "model_name": str(get_setting("vision.object_detection_model", "yolov8n.pt") or "yolov8n.pt"),
        "confidence": float(get_setting("vision.object_detection_confidence", 0.45) or 0.45),
        "person_confidence": float(get_setting("vision.object_detection_person_confidence", 0.68) or 0.68),
        "min_area_ratio": float(get_setting("vision.object_detection_min_area_ratio", 0.0015) or 0.0015),
        "person_min_area_ratio": float(get_setting("vision.object_detection_person_min_area_ratio", 0.03) or 0.03),
        "small_object_mode_enabled": bool(get_setting("vision.small_object_mode_enabled", False)),
        "small_object_crop_ratio": float(get_setting("vision.small_object_crop_ratio", 0.55) or 0.55),
        "camera_index": int(get_setting("vision.object_detection_camera_index", 0) or 0),
        "announce_seconds": float(get_setting("vision.object_detection_announce_seconds", 5.0) or 5.0),
        "show_overlay": bool(get_setting("vision.object_detection_show_overlay", True)),
        "watch_alert_cooldown_seconds": float(get_setting("vision.watch_alert_cooldown_seconds", 8.0) or 8.0),
        "alert_profile": str(get_setting("vision.object_detection_alert_profile", "balanced") or "balanced"),
    }


def is_object_detection_available():
    return YOLO is not None


def object_detection_import_error():
    if _IMPORT_ERROR:
        return f"Object detection dependency missing: {_IMPORT_ERROR}"
    return ""


def get_object_detection_model_name():
    return str(get_setting("vision.object_detection_model", "yolov8n.pt") or "yolov8n.pt")


def set_object_detection_model_name(model_name):
    global _MODEL
    cleaned = str(model_name or "").strip()
    if not cleaned:
        raise ValueError("Model name cannot be empty.")
    update_setting("vision.object_detection_model", cleaned)
    _MODEL = None
    return cleaned


def set_small_object_mode(enabled):
    update_setting("vision.small_object_mode_enabled", bool(enabled))


def is_small_object_mode_enabled():
    return bool(get_setting("vision.small_object_mode_enabled", False))


def get_watch_alert_cooldown_seconds():
    return float(get_setting("vision.watch_alert_cooldown_seconds", 8.0) or 8.0)


def set_watch_alert_cooldown_seconds(seconds):
    value = max(1.0, float(seconds))
    update_setting("vision.watch_alert_cooldown_seconds", value)
    return value


def get_object_detection_alert_profile():
    return str(get_setting("vision.object_detection_alert_profile", "balanced") or "balanced")


def apply_object_detection_alert_profile(profile_name):
    profile = str(profile_name or "").strip().lower()
    presets = {
        "fast": {"announce_seconds": 2.5, "cooldown_seconds": 3.0},
        "balanced": {"announce_seconds": 5.0, "cooldown_seconds": 8.0},
        "quiet": {"announce_seconds": 9.0, "cooldown_seconds": 14.0},
    }
    if profile not in presets:
        raise ValueError("Use object alert profile fast, balanced, or quiet.")

    selected = presets[profile]
    update_setting("vision.object_detection_alert_profile", profile)
    update_setting("vision.object_detection_announce_seconds", float(selected["announce_seconds"]))
    update_setting("vision.watch_alert_cooldown_seconds", float(selected["cooldown_seconds"]))
    return {
        "profile": profile,
        "announce_seconds": float(selected["announce_seconds"]),
        "cooldown_seconds": float(selected["cooldown_seconds"]),
    }


def reset_object_detection_model():
    return set_object_detection_model_name("yolov8n.pt")


def get_object_detection_presets():
    presets = get_setting("vision.object_detection_presets", [])
    if not isinstance(presets, list):
        return []
    cleaned = []
    for item in presets:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        model = str(item.get("model") or "").strip()
        if name and model:
            cleaned.append({"name": name, "model": model})
    return cleaned


def save_object_detection_preset(name, model_name):
    cleaned_name = str(name or "").strip()
    cleaned_model = str(model_name or "").strip()
    if not cleaned_name or not cleaned_model:
        raise ValueError("Preset name and model path are required.")
    presets = [preset for preset in get_object_detection_presets() if preset["name"].lower() != cleaned_name.lower()]
    presets.append({"name": cleaned_name, "model": cleaned_model})
    update_setting("vision.object_detection_presets", presets)
    return {"name": cleaned_name, "model": cleaned_model}


def use_object_detection_preset(name):
    cleaned_name = str(name or "").strip().lower()
    if not cleaned_name:
        raise ValueError("Preset name is required.")
    for preset in get_object_detection_presets():
        if preset["name"].lower() == cleaned_name:
            set_object_detection_model_name(preset["model"])
            return preset
    raise ValueError(f"I could not find an object model preset named {name}.")


def delete_object_detection_preset(name):
    cleaned_name = str(name or "").strip().lower()
    if not cleaned_name:
        raise ValueError("Preset name is required.")
    presets = get_object_detection_presets()
    remaining = [preset for preset in presets if preset["name"].lower() != cleaned_name]
    if len(remaining) == len(presets):
        raise ValueError(f"I could not find an object model preset named {name}.")
    update_setting("vision.object_detection_presets", remaining)
    return True


def _ensure_model():
    global _MODEL
    if YOLO is None:
        raise RuntimeError(object_detection_import_error() or "Ultralytics is not installed.")
    if _MODEL is None:
        settings = _object_settings()
        _MODEL = YOLO(settings["model_name"])
    return _MODEL


def get_supported_object_labels(limit=None):
    model = _ensure_model()
    names = getattr(model, "names", {}) or {}
    labels = [str(value) for _, value in sorted(names.items(), key=lambda item: item[0])]
    if limit is not None:
        return labels[:limit]
    return labels


def _box_area_ratio(box, frame_width, frame_height):
    x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
    box_width = max(0.0, x2 - x1)
    box_height = max(0.0, y2 - y1)
    frame_area = max(1.0, float(frame_width * frame_height))
    return (box_width * box_height) / frame_area


def _iter_filtered_detections(result, settings, frame_shape):
    frame_height, frame_width = frame_shape[:2]
    boxes = getattr(result, "boxes", None)
    names = getattr(result, "names", {})

    if boxes is None:
        return

    for box in boxes:
        confidence = float(box.conf[0].item())
        cls_index = int(box.cls[0].item())
        label = str(names.get(cls_index, f"class {cls_index}"))
        min_confidence = settings["person_confidence"] if label.lower() == "person" else settings["confidence"]
        if confidence < min_confidence:
            continue

        area_ratio = _box_area_ratio(box, frame_width, frame_height)
        min_area_ratio = settings["person_min_area_ratio"] if label.lower() == "person" else settings["min_area_ratio"]
        if settings.get("small_object_mode_enabled") and label.lower() != "person":
            min_area_ratio *= 0.35
        if area_ratio < min_area_ratio:
            continue

        yield {
            "label": label,
            "confidence": confidence,
            "xyxy": [int(value) for value in box.xyxy[0].tolist()],
            "area_ratio": area_ratio,
        }


def _detect_on_frame(frame, model, settings):
    result = model(frame, verbose=False)[0]
    return list(_iter_filtered_detections(result, settings, frame.shape))


def _map_crop_detection_to_frame(detection, crop_x, crop_y):
    x1, y1, x2, y2 = detection["xyxy"]
    mapped = dict(detection)
    mapped["xyxy"] = [x1 + crop_x, y1 + crop_y, x2 + crop_x, y2 + crop_y]
    return mapped


def _run_detection_passes(frame, model, settings):
    detections = _detect_on_frame(frame, model, settings)

    if not settings.get("small_object_mode_enabled"):
        return detections

    frame_height, frame_width = frame.shape[:2]
    crop_ratio = max(0.25, min(0.9, float(settings.get("small_object_crop_ratio", 0.55))))
    crop_width = max(1, int(frame_width * crop_ratio))
    crop_height = max(1, int(frame_height * crop_ratio))
    crop_x = max(0, (frame_width - crop_width) // 2)
    crop_y = max(0, (frame_height - crop_height) // 2)
    crop = frame[crop_y:crop_y + crop_height, crop_x:crop_x + crop_width]

    if crop.size == 0:
        return detections

    crop_detections = [
        _map_crop_detection_to_frame(detection, crop_x, crop_y)
        for detection in _detect_on_frame(crop, model, settings)
    ]
    detections.extend(crop_detections)
    return detections


def _labels_to_summary(labels):
    if not labels:
        return "I do not see any known objects right now."
    counts = Counter(labels)
    ordered = [f"{count} {label}" if count > 1 else label for label, count in counts.most_common(6)]
    return "I can see " + ", ".join(ordered) + "."


def get_latest_detection_summary(max_age_seconds=10):
    with _STATE_LOCK:
        labels = list(_LATEST_LABELS)
        updated_at = _LATEST_UPDATED_AT
    if not labels:
        return "No recent object detection results yet."
    if time.time() - updated_at > max_age_seconds:
        return "Object detection is idle right now."
    return _labels_to_summary(labels)


def set_watch_target(target):
    global _WATCH_TARGET, _WATCH_LAST_SEEN_AT, _WATCH_LAST_ALERT_AT
    cleaned = str(target or "").strip().lower()
    with _STATE_LOCK:
        _WATCH_TARGET = cleaned
        _WATCH_LAST_SEEN_AT = 0.0
        _WATCH_LAST_ALERT_AT = 0.0


def clear_watch_target():
    set_watch_target("")


def get_watch_status():
    with _STATE_LOCK:
        target = _WATCH_TARGET
        last_seen_at = _WATCH_LAST_SEEN_AT
        last_alert_at = _WATCH_LAST_ALERT_AT
        labels = list(_LATEST_LABELS)
    cooldown_seconds = get_watch_alert_cooldown_seconds()
    if not target:
        return {
            "active": False,
            "target": "",
            "cooldown_seconds": cooldown_seconds,
            "summary": "No object watch is active.",
        }
    visible = any(label.lower() == target for label in labels)
    if visible:
        summary = f"Watching for {target}. It is visible now."
    elif last_seen_at:
        summary = f"Watching for {target}. Last seen recently."
    else:
        summary = f"Watching for {target}. Not visible yet."
    return {
        "active": True,
        "target": target,
        "visible": visible,
        "last_seen_at": last_seen_at,
        "last_alert_at": last_alert_at,
        "cooldown_seconds": cooldown_seconds,
        "summary": summary,
    }


def get_detection_history(limit=8):
    with _STATE_LOCK:
        history = list(_DETECTION_HISTORY[-limit:])
    history.reverse()
    return history


def get_watch_event_history(limit=8):
    with _STATE_LOCK:
        history = list(_WATCH_EVENT_HISTORY[-limit:])
    history.reverse()
    return history


def clear_detection_history():
    with _STATE_LOCK:
        _DETECTION_HISTORY.clear()
        _WATCH_EVENT_HISTORY.clear()


def consume_watch_alert(cooldown_seconds=None):
    global _WATCH_LAST_ALERT_AT
    cooldown_seconds = (
        get_watch_alert_cooldown_seconds()
        if cooldown_seconds is None
        else max(1.0, float(cooldown_seconds))
    )
    with _STATE_LOCK:
        target = _WATCH_TARGET
        labels = list(_LATEST_LABELS)
        last_alert_at = _WATCH_LAST_ALERT_AT
        now = time.time()

        if not target:
            return None

        if not any(label.lower() == target for label in labels):
            return None

        if last_alert_at and (now - last_alert_at) < cooldown_seconds:
            return None

        _WATCH_LAST_ALERT_AT = now
        alert = {
            "target": target,
            "labels": labels,
            "summary": f"Alert: {target} is visible now.",
        }
        _append_history(
            _WATCH_EVENT_HISTORY,
            {
                "timestamp": now,
                "target": target,
                "labels": list(labels),
                "summary": alert["summary"],
            },
        )
        return alert


def detect_objects_once():
    settings = _object_settings()
    model = _ensure_model()
    cap = cv2.VideoCapture(settings["camera_index"])
    if not cap.isOpened():
        return {"ok": False, "error": "I could not open the camera."}
    success, frame = cap.read()
    cap.release()
    if not success:
        return {"ok": False, "error": "I could not capture a frame from the camera."}

    detections = _run_detection_passes(frame, model, settings)
    labels = [item["label"] for item in detections]
    _set_latest_labels(labels)
    return {
        "ok": True,
        "labels": labels,
        "summary": _labels_to_summary(labels),
    }


def detect_objects_on_screen():
    settings = _object_settings()
    model = _ensure_model()
    screenshot = pyautogui.screenshot()
    frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    detections = _run_detection_passes(frame, model, settings)
    labels = [item["label"] for item in detections]
    _set_latest_labels(labels)
    return {
        "ok": True,
        "labels": labels,
        "summary": _labels_to_summary(labels),
    }


def count_detected_object(target, labels):
    cleaned = str(target or "").strip().lower()
    if not cleaned:
        return 0
    return sum(1 for label in labels if label.lower() == cleaned)


def is_detected_object_visible(target, labels):
    return count_detected_object(target, labels) > 0


def run_object_detection(stop_event, on_stop=None, announce_callback=None):
    settings = _object_settings()
    model = _ensure_model()
    cap = cv2.VideoCapture(settings["camera_index"])
    if not cap.isOpened():
        if on_stop is not None:
            on_stop()
        raise RuntimeError("I could not open the camera for object detection.")

    last_announcement = 0.0
    last_signature = ""

    try:
        while not stop_event.is_set():
            success, frame = cap.read()
            if not success:
                break

            labels = []
            display_frame = frame.copy()
            detections = _run_detection_passes(frame, model, settings)

            for detection in detections:
                label = detection["label"]
                confidence = detection["confidence"]
                labels.append(label)

                if settings["show_overlay"]:
                    x1, y1, x2, y2 = detection["xyxy"]
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), (98, 68, 197), 2)
                    cv2.putText(
                        display_frame,
                        f"{label} {confidence:.2f}",
                        (x1, max(28, y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 196, 72),
                        2,
                        cv2.LINE_AA,
                    )

            _set_latest_labels(labels)

            signature = ",".join(sorted(labels))
            if announce_callback and labels and (
                signature != last_signature or time.time() - last_announcement >= settings["announce_seconds"]
            ):
                announce_callback(_labels_to_summary(labels))
                last_signature = signature
                last_announcement = time.time()

            if settings["show_overlay"]:
                status_line = _labels_to_summary(labels)
                cv2.putText(
                    display_frame,
                    "Object Detection Active",
                    (16, 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 196, 72),
                    2,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    display_frame,
                    status_line[:90],
                    (16, 56),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (240, 240, 250),
                    2,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    display_frame,
                    "Press ESC to stop",
                    (16, 82),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (210, 210, 220),
                    2,
                    cv2.LINE_AA,
                )
                if settings.get("small_object_mode_enabled"):
                    cv2.putText(
                        display_frame,
                        "Small Object Mode On",
                        (16, 108),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (255, 196, 72),
                        2,
                        cv2.LINE_AA,
                    )
                cv2.imshow("Grandpa Assistant Object Detection", display_frame)

            if cv2.waitKey(1) & 0xFF == 27:
                stop_event.set()
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if on_stop is not None:
            on_stop()
