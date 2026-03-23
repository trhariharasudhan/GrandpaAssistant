import os
import threading

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    pystray = None
    Image = None
    ImageDraw = None

try:
    import ctypes
except ImportError:
    ctypes = None


_tray_icon = None
_tray_thread = None
_exit_callback = None


def is_tray_available():
    return pystray is not None and Image is not None and ImageDraw is not None


def set_tray_exit_callback(callback):
    global _exit_callback
    _exit_callback = callback


def _get_console_window():
    if os.name != "nt" or ctypes is None:
        return None
    return ctypes.windll.kernel32.GetConsoleWindow()


def hide_console():
    hwnd = _get_console_window()
    if not hwnd:
        return False
    ctypes.windll.user32.ShowWindow(hwnd, 0)
    return True


def show_console():
    hwnd = _get_console_window()
    if not hwnd:
        return False
    ctypes.windll.user32.ShowWindow(hwnd, 5)
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    return True


def _create_icon_image():
    image = Image.new("RGB", (64, 64), color=(24, 24, 28))
    draw = ImageDraw.Draw(image)
    draw.ellipse((10, 10, 54, 54), fill=(240, 240, 240))
    draw.ellipse((22, 18, 42, 46), fill=(24, 24, 28))
    return image


def start_tray(on_quit=None):
    global _tray_icon, _tray_thread

    if not is_tray_available():
        return False, "Tray mode needs pystray and Pillow installed."

    if _tray_icon is not None:
        hide_console()
        return True, "Assistant is already running in the system tray."

    def restore_action(icon, item):
        show_console()
        icon.notify("Grandpa Assistant restored.")

    def quit_action(icon, item):
        icon.stop()
        callback = on_quit or _exit_callback
        if callback:
            callback()

    menu = pystray.Menu(
        pystray.MenuItem("Open Grandpa Assistant", restore_action),
        pystray.MenuItem("Exit Assistant", quit_action),
    )

    _tray_icon = pystray.Icon(
        "GrandpaAssistant",
        _create_icon_image(),
        "Grandpa Assistant",
        menu,
    )

    def run_icon():
        try:
            _tray_icon.run()
        finally:
            _clear_tray()

    _tray_thread = threading.Thread(target=run_icon, daemon=True)
    _tray_thread.start()
    hide_console()
    return True, "Grandpa Assistant moved to the system tray."


def stop_tray():
    global _tray_icon
    if _tray_icon is None:
        return False

    _tray_icon.stop()
    _clear_tray()
    show_console()
    return True


def _clear_tray():
    global _tray_icon, _tray_thread
    _tray_icon = None
    _tray_thread = None
