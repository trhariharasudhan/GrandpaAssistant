import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for path in [APP_DIR, SHARED_DIR, FEATURES_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

from voice import listen as listen_module
from vision import object_detection, screen_reader


class OptionalDependencyGuardTests(unittest.TestCase):
    def test_listen_returns_none_when_speech_recognition_missing(self) -> None:
        with patch.object(listen_module, "sr", None), patch.object(listen_module, "recognizer", None):
            result = listen_module.listen()

        self.assertIsNone(result)
        self.assertEqual(listen_module.stt_backend_payload()["last_backend_used"], "unavailable")
        self.assertIn("SpeechRecognition", listen_module.stt_backend_payload()["last_error"])

    def test_listen_returns_none_when_microphone_backend_fails(self) -> None:
        class BrokenMicrophone:
            def __enter__(self):
                raise OSError("No Default Input Device Available")

            def __exit__(self, *_args):
                return False

        class FakeSpeechRecognition:
            class WaitTimeoutError(Exception):
                pass

            class UnknownValueError(Exception):
                pass

            @staticmethod
            def Microphone():
                return BrokenMicrophone()

        with patch.object(listen_module, "sr", FakeSpeechRecognition), patch.object(listen_module, "recognizer", SimpleNamespace()):
            result = listen_module.listen()

        self.assertIsNone(result)
        self.assertIn("No Default Input Device", listen_module.stt_backend_payload()["last_error"])

    def test_object_detection_reports_missing_opencv_without_raising(self) -> None:
        with patch.object(object_detection, "cv2", None), patch.object(object_detection, "_CV2_IMPORT_ERROR", "missing cv2"):
            self.assertFalse(object_detection.is_object_detection_available())
            self.assertIn("OpenCV", object_detection.object_detection_import_error())

    def test_screen_reader_reports_ocr_unavailable_without_capture(self) -> None:
        with patch.object(screen_reader, "pytesseract", None):
            self.assertFalse(screen_reader._ocr_ready())
            self.assertEqual(screen_reader.read_screen_text(), "Tesseract OCR is not installed or not available in PATH.")


if __name__ == "__main__":
    unittest.main()
