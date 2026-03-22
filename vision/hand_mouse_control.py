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
alpha = 0.2
frame_margin = 100

prev_zoom_distance = 0
zoom_threshold = 20

scroll_cooldown = 0
scroll_delay = 0.3

two_hand_counter = 0
zoom_mode_active = False

click_threshold = 30
double_click_delay = 0.4
hold_threshold = 0.5

pinch_start_time = 0
last_tap_time = 0
dragging = False


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


def run_hand_mouse(stop_event, on_stop=None):
    global prev_x, prev_y
    global prev_zoom_distance, two_hand_counter, zoom_mode_active
    global pinch_start_time, last_tap_time, dragging
    global scroll_cooldown

    model_url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    model_path = "hand_landmarker.task"
    if not os.path.exists(model_path):
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
                    if current_time - scroll_cooldown > scroll_delay:
                        pyautogui.scroll(80)
                        scroll_cooldown = current_time
                    prev_zoom_distance = 0

                elif left_open and not right_open:
                    if current_time - scroll_cooldown > scroll_delay:
                        pyautogui.scroll(-80)
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
                        if zoom_distance - prev_zoom_distance > zoom_threshold:
                            pyautogui.keyDown("ctrl")
                            pyautogui.scroll(80)
                            pyautogui.keyUp("ctrl")
                        elif prev_zoom_distance - zoom_distance > zoom_threshold:
                            pyautogui.keyDown("ctrl")
                            pyautogui.scroll(-80)
                            pyautogui.keyUp("ctrl")

                    prev_zoom_distance = zoom_distance
                else:
                    prev_zoom_distance = 0

            elif not zoom_mode_active and len(detection_result.hand_landmarks) == 1:
                hand_landmarks = detection_result.hand_landmarks[0]
                handedness = detection_result.handedness[0][0].category_name

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

                    mouse_x = np.interp(
                        ix, (frame_margin, w - frame_margin), (0, screen_width)
                    )
                    mouse_y = np.interp(
                        iy, (frame_margin, h - frame_margin), (0, screen_height)
                    )

                    curr_x = prev_x + (mouse_x - prev_x) * alpha
                    curr_y = prev_y + (mouse_y - prev_y) * alpha

                    pyautogui.moveTo(curr_x, curr_y)
                    prev_x, prev_y = curr_x, curr_y

                    current_time = time.time()
                    thumb_index_dist = math.hypot(ix - thumb_x, iy - thumb_y)
                    thumb_middle_dist = math.hypot(
                        middle_x - thumb_x, middle_y - thumb_y
                    )

                    if thumb_middle_dist < click_threshold:
                        pyautogui.rightClick()
                        time.sleep(0.3)

                    if thumb_index_dist < click_threshold:
                        if pinch_start_time == 0:
                            pinch_start_time = current_time

                        hold_time = current_time - pinch_start_time
                        if hold_time > hold_threshold and not dragging:
                            pyautogui.mouseDown()
                            dragging = True
                    else:
                        if dragging:
                            pyautogui.mouseUp()
                            dragging = False

                        if pinch_start_time != 0:
                            tap_duration = current_time - pinch_start_time
                            if tap_duration < hold_threshold:
                                if current_time - last_tap_time < double_click_delay:
                                    pyautogui.doubleClick()
                                    last_tap_time = 0
                                else:
                                    pyautogui.click()
                                    last_tap_time = current_time

                        pinch_start_time = 0
        else:
            prev_zoom_distance = 0

        cv2.imshow("Hand Mouse Control", img)

        if cv2.waitKey(1) & 0xFF == 27:
            stop_event.set()
            break

    cap.release()
    cv2.destroyAllWindows()

    if on_stop is not None:
        on_stop()


def stop_hand_mouse():
    pass


if __name__ == "__main__":
    import threading

    stop_event = threading.Event()
    run_hand_mouse(stop_event)
