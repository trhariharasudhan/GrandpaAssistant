import speech_recognition as sr

recognizer = sr.Recognizer()


def listen():
    with sr.Microphone() as source:
        try:
            # Ambient noise calibration
            recognizer.adjust_for_ambient_noise(source, duration=1)

            audio = recognizer.listen(source, timeout=1, phrase_time_limit=3)

            command = recognizer.recognize_google(audio)

            return command.lower()

        except sr.WaitTimeoutError:
            return None

        except:
            return None
