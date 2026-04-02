import contextlib
import math
import os
import sys
import time
import urllib.request

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# Suppress noisy native logs before MediaPipe starts.
devnull = open(os.devnull, "w")
old_stderr = os.dup(2)
os.dup2(devnull.fileno(), 2)

import cv2
import mediapipe as mp
import numpy as np
import pyautogui
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from utils.config import get_setting


@contextlib.contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as fnull:
        old_stdout = sys.stdout
        sys.stdout = fnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


screen_width, screen_height = pyautogui.size()

prev_x, prev_y = 0, 0
prev_zoom_distance = 0
scroll_cooldown = 0
two_hand_counter = 0
zoom_mode_active = False
pinch_start_time = 0
last_tap_time = 0
last_right_click_time = 0
dragging = False
pinch_frames = 0
right_click_frames = 0
fist_hold_start_time = 0


def _settings():
    return {
        "alpha": float(get_setting("hand_mouse.smoothing_alpha", 0.22) or 0.22),
        "frame_margin": int(get_setting("hand_mouse.frame_margin", 90) or 90),
        "zoom_threshold": float(get_setting("hand_mouse.zoom_threshold", 24) or 24),
        "scroll_delay": float(get_setting("hand_mouse.scroll_delay_seconds", 0.28) or 0.28),
        "scroll_amount": int(get_setting("hand_mouse.scroll_amount", 80) or 80),
        "click_threshold": float(get_setting("hand_mouse.click_threshold", 28) or 28),
        "gesture_stability_frames": max(1, int(get_setting("hand_mouse.gesture_stability_frames", 3) or 3)),
        "double_click_delay": float(get_setting("hand_mouse.double_click_delay_seconds", 0.4) or 0.4),
        "hold_threshold": float(get_setting("hand_mouse.hold_threshold_seconds", 0.55) or 0.55),
        "right_click_cooldown": float(get_setting("hand_mouse.right_click_cooldown_seconds", 0.6) or 0.6),
        "exit_hold_seconds": float(get_setting("hand_mouse.exit_hold_seconds", 1.4) or 1.4),
        "show_overlay": bool(get_setting("hand_mouse.show_overlay", True)),
    }


def _reset_runtime_state():
    global prev_x, prev_y
    global prev_zoom_distance, scroll_cooldown, two_hand_counter, zoom_mode_active
    global pinch_start_time, last_tap_time, last_right_click_time
    global dragging, pinch_frames, right_click_frames, fist_hold_start_time
    prev_x = 0
    prev_y = 0
    prev_zoom_distance = 0
    scroll_cooldown = 0
    two_hand_counter = 0
    zoom_mode_active = False
    pinch_start_time = 0
    last_tap_time = 0
    last_right_click_time = 0
    dragging = False
    pinch_frames = 0
    right_click_frames = 0
    fist_hold_start_time = 0


def is_palm_facing_camera(hand_landmarks, handedness_label):
    if handedness_label == "Right":
        return hand_landmarks[5].x > hand_landmarks[17].x
    return hand_landmarks[5].x < hand_landmarks[17].x


def is_hand_open(hand_landmarks):
    index_open = hand_landmarks[8].y < hand_landmarks[6].y
    middle_open = hand_landmarks[12].y < hand_landmarks[10].y
    ring_open = hand_landmarks[16].y < hand_landmarks[14].y
    pinky_open = hand_landmarks[20].y < hand_landmarks[18].y
    return index_open and middle_open and ring_open and pinky_open


def _draw_status(img, lines):
    y = 28
    for line in lines:
        cv2.putText(
            img,
            line,
            (16, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (40, 240, 180),
            2,
            cv2.LINE_AA,
        )
        y += 24


def run_hand_mouse(stop_event, on_stop=None):
    global prev_x, prev_y
    global prev_zoom_distance, two_hand_counter, zoom_mode_active
    global pinch_start_time, last_tap_time, dragging
    global scroll_cooldown, last_right_click_time, pinch_frames
    global right_click_frames, fist_hold_start_time

    settings = _settings()
    _reset_runtime_state()
    model_url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    model_path = os.path.join(base_dir, "assets", "models", "hand_landmarker.task")
    if not os.path.exists(model_path):
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        urllib.request.urlretrieve(model_url, model_path)

    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    with suppress_stdout():
        detector = vision.HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        if on_stop is not None:
            on_stop()
        return

    status_line = "Move: open palm | Left click: thumb+index | Right click: thumb+middle"

    while not stop_event.is_set():
        success, img = cap.read()
        if not success:
            break

        img = cv2.flip(img, 1)
        h, w, _ = img.shape

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB),
        )
        detection_result = detector.detect(mp_image)

        if detection_result.hand_landmarks:
            if len(detection_result.hand_landmarks) == 2:
                two_hand_counter += 1
            else:
                two_hand_counter = 0

            zoom_mode_active = two_hand_counter > 5

            if zoom_mode_active and len(detection_result.hand_landmarks) == 2:
                hand1 = detection_result.hand_landmarks[0]
                hand2 = detection_result.hand_landmarks[1]

                handedness1 = detection_result.handedness[0][0].category_name
                handedness2 = detection_result.handedness[1][0].category_name
                current_time = time.time()

                if handedness1 == "Left":
                    left_hand = hand1
                    right_hand = hand2
                else:
                    left_hand = hand2
                    right_hand = hand1

                left_open = is_hand_open(left_hand)
                right_open = is_hand_open(right_hand)

                if not left_open and right_open:
                    status_line = "Scroll up"
                    if current_time - scroll_cooldown > settings["scroll_delay"]:
                        pyautogui.scroll(settings["scroll_amount"])
                        scroll_cooldown = current_time
                    prev_zoom_distance = 0

                elif left_open and not right_open:
                    status_line = "Scroll down"
                    if current_time - scroll_cooldown > settings["scroll_delay"]:
                        pyautogui.scroll(-settings["scroll_amount"])
                        scroll_cooldown = current_time
                    prev_zoom_distance = 0

                elif (
                    left_open
                    and right_open
                    and is_palm_facing_camera(hand1, handedness1)
                    and is_palm_facing_camera(hand2, handedness2)
                ):
                    x1 = int(hand1[8].x * w)
                    y1 = int(hand1[8].y * h)
                    x2 = int(hand2[8].x * w)
                    y2 = int(hand2[8].y * h)
                    zoom_distance = math.hypot(x2 - x1, y2 - y1)

                    if prev_zoom_distance != 0:
                        if zoom_distance - prev_zoom_distance > settings["zoom_threshold"]:
                            status_line = "Zoom in"
                            pyautogui.keyDown("ctrl")
                            pyautogui.scroll(settings["scroll_amount"])
                            pyautogui.keyUp("ctrl")
                        elif prev_zoom_distance - zoom_distance > settings["zoom_threshold"]:
                            status_line = "Zoom out"
                            pyautogui.keyDown("ctrl")
                            pyautogui.scroll(-settings["scroll_amount"])
                            pyautogui.keyUp("ctrl")

                    prev_zoom_distance = zoom_distance
                else:
                    prev_zoom_distance = 0

            elif not zoom_mode_active and len(detection_result.hand_landmarks) == 1:
                hand_landmarks = detection_result.hand_landmarks[0]
                handedness = detection_result.handedness[0][0].category_name
                current_time = time.time()

                ix = int(hand_landmarks[8].x * w)
                iy = int(hand_landmarks[8].y * h)
                thumb_x = int(hand_landmarks[4].x * w)
                thumb_y = int(hand_landmarks[4].y * h)
                middle_x = int(hand_landmarks[12].x * w)
                middle_y = int(hand_landmarks[12].y * h)

                cv2.circle(img, (ix, iy), 8, (0, 255, 255), -1)
                cv2.circle(img, (ix, iy), 16, (0, 255, 255), 2)
                cv2.circle(img, (thumb_x, thumb_y), 6, (0, 255, 255), -1)
                cv2.circle(img, (middle_x, middle_y), 6, (0, 255, 255), -1)

                if is_palm_facing_camera(hand_landmarks, handedness):
                    prev_zoom_distance = 0
                    fist_hold_start_time = 0

                    mouse_x = np.interp(
                        ix, (settings["frame_margin"], w - settings["frame_margin"]), (0, screen_width)
                    )
                    mouse_y = np.interp(
                        iy, (settings["frame_margin"], h - settings["frame_margin"]), (0, screen_height)
                    )

                    curr_x = prev_x + (mouse_x - prev_x) * settings["alpha"]
                    curr_y = prev_y + (mouse_y - prev_y) * settings["alpha"]

                    pyautogui.moveTo(curr_x, curr_y)
                    prev_x, prev_y = curr_x, curr_y

                    thumb_index_dist = math.hypot(ix - thumb_x, iy - thumb_y)
                    thumb_middle_dist = math.hypot(
                        middle_x - thumb_x, middle_y - thumb_y
                    )

                    if thumb_middle_dist < settings["click_threshold"]:
                        right_click_frames += 1
                    else:
                        right_click_frames = 0

                    if (
                        right_click_frames >= settings["gesture_stability_frames"]
                        and current_time - last_right_click_time > settings["right_click_cooldown"]
                    ):
                        pyautogui.rightClick()
                        last_right_click_time = current_time
                        right_click_frames = 0
                        status_line = "Right click"

                    if thumb_index_dist < settings["click_threshold"]:
                        pinch_frames += 1
                        if pinch_start_time == 0:
                            pinch_start_time = current_time

                        hold_time = current_time - pinch_start_time
                        if (
                            pinch_frames >= settings["gesture_stability_frames"]
                            and hold_time > settings["hold_threshold"]
                            and not dragging
                        ):
                            pyautogui.mouseDown()
                            dragging = True
                            status_line = "Drag"
                    else:
                        if dragging:
                            pyautogui.mouseUp()
                            dragging = False
                            status_line = "Drop"

                        if pinch_start_time != 0:
                            tap_duration = current_time - pinch_start_time
                            if (
                                pinch_frames >= settings["gesture_stability_frames"]
                                and tap_duration < settings["hold_threshold"]
                            ):
                                if current_time - last_tap_time < settings["double_click_delay"]:
                                    pyautogui.doubleClick()
                                    last_tap_time = 0
                                    status_line = "Double click"
                                else:
                                    pyautogui.click()
                                    last_tap_time = current_time
                                    status_line = "Left click"

                        pinch_start_time = 0
                        pinch_frames = 0
                else:
                    pinch_frames = 0
                    right_click_frames = 0
                    if dragging:
                        pyautogui.mouseUp()
                        dragging = False
                    if not is_hand_open(hand_landmarks):
                        if fist_hold_start_time == 0:
                            fist_hold_start_time = current_time
                        remaining = max(
                            0.0,
                            settings["exit_hold_seconds"] - (current_time - fist_hold_start_time),
                        )
                        status_line = f"Hold fist to exit: {remaining:.1f}s"
                        if current_time - fist_hold_start_time >= settings["exit_hold_seconds"]:
                            stop_event.set()
                            break
                    else:
                        fist_hold_start_time = 0
                        status_line = "Rotate palm to control cursor"
        else:
            prev_zoom_distance = 0
            pinch_frames = 0
            right_click_frames = 0
            fist_hold_start_time = 0
            status_line = "Show your hand to start"

        if settings["show_overlay"]:
            mode_line = "Mode: zoom/scroll" if zoom_mode_active else "Mode: cursor"
            help_line = "Esc closes window | Fist hold exits"
            _draw_status(img, [mode_line, status_line, help_line])

        cv2.imshow("Hand Mouse Control", img)

        if cv2.waitKey(1) & 0xFF == 27:
            stop_event.set()
            break

    cap.release()
    cv2.destroyAllWindows()
    if dragging:
        pyautogui.mouseUp()
    _reset_runtime_state()

    if on_stop is not None:
        on_stop()


def stop_hand_mouse():
    pass


if __name__ == "__main__":
    import threading

    stop_event = threading.Event()
    run_hand_mouse(stop_event)
