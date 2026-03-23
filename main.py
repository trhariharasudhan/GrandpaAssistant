import sys

from core.assistant import main

if __name__ == "__main__":
    main(start_in_tray="--tray" in sys.argv)
