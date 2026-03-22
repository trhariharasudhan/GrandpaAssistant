import os
import psutil
import pygetwindow as gw
import pyautogui
import datetime
from voice.speak import speak
from voice.listen import listen

# ================= BASIC SYSTEM CONTROLS =================


def sleep_system():
    speak("Putting the system to sleep")
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")


def lock_system():
    speak("Locking the system")
    os.system("rundll32.exe user32.dll,LockWorkStation")


def switch_user():
    speak("Switching user")
    os.system("tsdiscon")


def sign_out():
    speak("Signing out")
    os.system("shutdown /l")


def perform_sign_out():
    os.system("shutdown /l")


def restart_system(confirm_mode="voice"):
    if confirm_mode == "text":
        speak("Are you sure you want to restart?")
        confirm = input("Confirm restart (yes/no): ").strip().lower()
    else:
        speak("Are you sure you want to restart? Say yes to confirm.")
        confirm = listen()

    if confirm and "yes" in confirm.lower():
        speak("Restarting the system")
        os.system("shutdown /r /t 5")
    else:
        speak("Restart cancelled")


def perform_restart():
    os.system("shutdown /r /t 5")


def shutdown_system(confirm_mode="voice"):
    if confirm_mode == "text":
        speak("Are you sure you want to shut down?")
        confirm = input("Confirm shutdown (yes/no): ").strip().lower()
    else:
        speak("Are you sure you want to shut down? Say yes to confirm.")
        confirm = listen()

    if confirm and "yes" in confirm.lower():
        speak("Shutting down the system")
        os.system("shutdown /s /t 5")
    else:
        speak("Shutdown cancelled")


def perform_shutdown():
    os.system("shutdown /s /t 5")


# ================= SCREENSHOT & BATTERY =================


def take_screenshot():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_path = os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots")

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    filename = os.path.join(folder_path, f"screenshot_{timestamp}.png")
    pyautogui.screenshot(filename)
    speak("Screenshot taken successfully.")


def get_battery_info():
    battery = psutil.sensors_battery()

    if battery is None:
        return "Unable to get battery information."

    percent = battery.percent
    plugged = battery.power_plugged

    if plugged:
        return f"Battery is at {percent}% and charging"
    else:
        return f"Battery is at {percent}% and not charging"


# ================= NETWORK CONTROLS =================


def handle_wifi(command):
    if "wifi" in command or "wi fi" in command:
        speak("Opening WiFi settings")
        os.system("start ms-settings:network-wifi")
        return True
    return False


def handle_bluetooth(command):
    if "bluetooth" in command:
        speak("Opening Bluetooth settings")
        os.system("start ms-settings:bluetooth")
        return True
    return False


def handle_airplane(command):
    if "airplane" in command or "flight mode" in command:
        speak("Opening Airplane mode settings")
        os.system("start ms-settings:network-airplanemode")
        return True
    return False


# ================= APPLICATION WINDOW MANAGEMENT =================


def open_explorer():
    speak("Opening File Explorer")
    os.startfile("C:\\")


def close_app(command):
    app_name = command.replace("close", "").strip().lower()
    exe_name = app_name + ".exe"
    closed = False

    for process in psutil.process_iter(["name"]):
        try:
            if process.info["name"] and process.info["name"].lower() == exe_name:
                process.kill()
                closed = True
        except Exception:
            pass

    if closed:
        speak(f"Closing {app_name}")
    else:
        speak("Application not running")


def minimize_app(command):
    app = command.replace("minimize", "").strip()
    if app:
        windows = gw.getWindowsWithTitle(app)
        if windows:
            windows[0].minimize()
            speak(f"Minimized {app}")
        else:
            speak("Could not find that application window")
    else:
        speak("Please specify which application to minimize")


def maximize_app(command):
    app = command.replace("maximize", "").strip()
    if app:
        windows = gw.getWindowsWithTitle(app)
        if windows:
            windows[0].maximize()
            windows[0].activate()
            speak(f"Maximized {app}")
        else:
            speak("Could not find that application window")
    else:
        speak("Please specify which application to maximize")


def restore_app(command):
    app = command.replace("restore", "").strip()
    if app:
        windows = gw.getWindowsWithTitle(app)
        if windows:
            windows[0].restore()
            windows[0].activate()
            speak(f"Restored {app}")
        else:
            speak("Could not find that application window")
    else:
        speak("Please specify which application to restore")


def switch_to_app(command):
    app = command.replace("switch to", "").strip()
    if app:
        windows = gw.getWindowsWithTitle(app)
        if windows:
            windows[0].activate()
            speak(f"Switched to {app}")
        else:
            speak("Could not find that application window")
    else:
        speak("Please specify which application to switch to")


# ================= FUN UTILITIES =================


def tell_joke():
    import pyjokes

    return pyjokes.get_joke()
