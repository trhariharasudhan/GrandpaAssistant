import os
import json
import time

from utils.paths import backend_data_path

PROFILE_PATH = backend_data_path("face_profile.json")

def _get_camera_frame(camera_index=0, retries=5):
    try:
        import cv2
    except ImportError:
        return None, "OpenCV is not installed."

    cap = cv2.VideoCapture(camera_index)
    
    # Warm up camera briefly
    for _ in range(5):
        cap.read()
        time.sleep(0.1)
        
    for _ in range(retries):
        ret, frame = cap.read()
        if ret and frame is not None:
            cap.release()
            return frame, "Success"
        time.sleep(0.5)

    cap.release()
    return None, "Failed to capture frame from webcam."

def _extract_face_embedding(img_array):
    try:
        from deepface import DeepFace
    except ImportError:
        return None, "DeepFace is not installed."

    try:
        # Get embeddings. enforce_detection=True ensures there is actually a face.
        # We use a lightweight model like Facenet512 or VGG-Face.
        result = DeepFace.represent(img_path=img_array, model_name="VGG-Face", enforce_detection=True)
        if not result:
            return None, "No face found in frame."
        # result is a list of dictionaries (one for each face detected). We take the first one.
        embedding = result[0].get("embedding")
        return embedding, "Success"
    except ValueError as e:
        # DeepFace raises ValueError if face goes undetected
        return None, "No face detected in the image."
    except Exception as e:
        return None, f"DeepFace error: {e}"

def _cosine_similarity(vec1, vec2):
    import math
    dot = sum(a*b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a*a for a in vec1))
    norm_b = math.sqrt(sum(b*b for b in vec2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

def is_face_enrolled():
    return os.path.exists(PROFILE_PATH)

def enroll_user_face(camera_index=0):
    frame, msg = _get_camera_frame(camera_index)
    if frame is None:
        return False, msg

    embedding, msg = _extract_face_embedding(frame)
    if embedding is None:
        return False, msg

    try:
        os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)
        with open(PROFILE_PATH, "w", encoding="utf-8") as f:
            json.dump({"user_embedding": embedding}, f)
        return True, "Face enrolled successfully."
    except Exception as e:
        return False, f"Failed to save profile: {e}"

def verify_user_face(camera_index=0, threshold=0.70):
    if not is_face_enrolled():
        return False, "No face profile enrolled."

    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            saved_embedding = data.get("user_embedding")
    except Exception:
        return False, "Failed to read saved profile."

    if not saved_embedding:
        return False, "Corrupted profile data."

    frame, msg = _get_camera_frame(camera_index)
    if frame is None:
        return False, msg

    current_embedding, msg = _extract_face_embedding(frame)
    if current_embedding is None:
        return False, msg

    # Compare embeddings
    sim = _cosine_similarity(saved_embedding, current_embedding)
    
    if sim >= threshold:
        return True, f"Face verified (Similarity: {sim:.2f})"
    else:
        return False, f"Face does not match (Similarity: {sim:.2f})"
