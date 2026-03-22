import os
from playsound import playsound


def play_sound(filename):
    try:
        base_path = os.path.dirname(os.path.dirname(__file__))
        sound_path = os.path.join(base_path, "sounds", filename)

        playsound(sound_path)

    except Exception as e:
        print("Sound error:", e)
