import sys
import os

APP_DIR = os.path.join(os.path.dirname(__file__), "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for path in [APP_DIR, SHARED_DIR, FEATURES_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

from core.assistant import main

if __name__ == "__main__":
    args = set(sys.argv[1:])
    start_in_tray = "--tray" in args
    start_in_ui = "--voice" not in args and "--text" not in args and not start_in_tray
    if "--ui" in args:
        start_in_ui = True
    main(start_in_tray=start_in_tray, start_in_ui=start_in_ui)
