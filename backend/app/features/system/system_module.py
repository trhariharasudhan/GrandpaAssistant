import os
import psutil
import pygetwindow as gw
import pyautogui
import datetime
import random
import subprocess
import time
import ctypes
import sys
import threading
import re
from voice.speak import speak
from voice.listen import listen
from utils.config import get_setting


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
BACKEND_MAIN_PATH = os.path.join(PROJECT_ROOT, "backend", "main.py")

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


def is_running_as_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_assistant_as_admin():
    if is_running_as_admin():
        return "Full control mode is already enabled with administrator access."

    python_exe = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = sys.executable

    if not os.path.exists(BACKEND_MAIN_PATH):
        return "I could not find backend/main.py to relaunch in admin mode."

    interface_mode = str(get_setting("startup.interface_mode", "terminal") or "terminal").strip().lower()
    terminal_input_mode = str(get_setting("startup.terminal_input_mode", "text") or "text").strip().lower()
    if terminal_input_mode not in {"text", "voice"}:
        terminal_input_mode = "text"
    launch_args = (
        f'"{BACKEND_MAIN_PATH}" --ui'
        if interface_mode == "ui"
        else f'"{BACKEND_MAIN_PATH}" --{terminal_input_mode}'
    )

    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            python_exe,
            launch_args,
            PROJECT_ROOT,
            1,
        )
    except Exception:
        result = 0

    if result and int(result) > 32:
        # Close the current non-admin process after reply so the elevated process can bind ports cleanly.
        def _delayed_exit():
            time.sleep(1.2)
            os._exit(0)

        threading.Thread(target=_delayed_exit, daemon=True).start()
        return (
            "Administrator relaunch started. Please approve the Windows UAC popup. "
            "This window will close automatically in a second."
        )
    return "I could not start administrator mode. Please run the assistant as Administrator manually."


def _run_powershell(command, timeout=10):
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0, (result.stdout or "").strip() or (result.stderr or "").strip()
    except Exception as error:
        return False, str(error)


def _is_permission_error(message):
    text = (message or "").lower()
    return any(
        token in text
        for token in [
            "access is denied",
            "requires elevation",
            "cannot open",
            "permission",
            "error 5",
            "generic failure",
            "hresult 0x80041001",
        ]
    )


def _open_settings(uri, label):
    speak(f"Opening {label}")
    os.system(f"start {uri}")


def _wifi_status_text():
    status_script = (
        "$adapter = Get-NetAdapter | "
        "Where-Object { $_.HardwareInterface -eq $true -and ($_.Name -match 'wi-?fi|wireless|wlan') } | "
        "Select-Object -First 1; "
        "if ($adapter) { Write-Output $adapter.Status } else { Write-Output 'UNKNOWN' }"
    )
    ok, output = _run_powershell(status_script)
    if not ok:
        return None
    value = (output or "").upper()
    if "UP" in value:
        return "on"
    if "DOWN" in value:
        return "off"
    return None


def _set_wifi_state(enable):
    action = "Enable" if enable else "Disable"
    command = (
        "$adapter = Get-NetAdapter | "
        "Where-Object { $_.HardwareInterface -eq $true -and ($_.Name -match 'wi-?fi|wireless|wlan') } | "
        "Select-Object -First 1; "
        "if (-not $adapter) { exit 3 }; "
        f"{action}-NetAdapter -Name $adapter.Name -Confirm:$false -ErrorAction Stop"
    )
    return _run_powershell(command)


def _bluetooth_service_status():
    ok, output = _run_powershell("(Get-Service bthserv -ErrorAction SilentlyContinue).Status")
    if not ok:
        return None
    value = (output or "").strip().lower()
    if "running" in value:
        return "on"
    if "stopped" in value:
        return "off"
    return None


def _set_bluetooth_service(enable):
    command = (
        "Start-Service bthserv -ErrorAction Stop"
        if enable
        else "Stop-Service bthserv -Force -ErrorAction Stop"
    )
    return _run_powershell(command)


def _bluetooth_radio_selector_script():
    return (
        "$devices = Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue; "
        "$radio = $devices | Where-Object { "
        "$name = $_.FriendlyName; "
        "$name -and "
        "$name -match 'bluetooth|radio|adapter' -and "
        "$name -notmatch 'enumerator|avrcp|a2dp|rfcomm|hid|gatt|device|audio|mouse|keyboard|headset|controller|remote' "
        "} | Select-Object -First 1; "
        "if (-not $radio) { "
        "$radio = $devices | Where-Object { $_.FriendlyName -and $_.FriendlyName -notmatch 'enumerator|avrcp|a2dp|rfcomm|hid|gatt' } | "
        "Select-Object -First 1 "
        "}; "
    )


def _bluetooth_adapter_status():
    command = (
        _bluetooth_radio_selector_script()
        + "if ($radio) { Write-Output $radio.Status } else { Write-Output 'UNKNOWN' }"
    )
    ok, output = _run_powershell(command)
    if not ok:
        return None
    value = (output or "").strip().upper()
    if value == "OK":
        return "on"
    if value in {"ERROR", "UNKNOWN", "DEGRADED"}:
        return "off"
    return None


def _set_bluetooth_radio_state(enable):
    action = "Enable-PnpDevice" if enable else "Disable-PnpDevice"
    command = (
        _bluetooth_radio_selector_script()
        + "if (-not $radio) { Write-Output 'NOT_FOUND'; exit 3 }; "
        + f"{action} -InstanceId $radio.InstanceId -Confirm:$false -ErrorAction Stop"
    )
    return _run_powershell(command)


def _camera_device_selector_script():
    return (
        "$devices = Get-PnpDevice -ErrorAction SilentlyContinue | "
        "Where-Object { $_.FriendlyName -and $_.FriendlyName -notmatch 'virtual|obs|droidcam|epoccam|dfu' }; "
        "$item = $devices | Where-Object { $_.Class -match 'Camera|Image' } | Select-Object -First 1; "
        "if (-not $item) { "
        "$item = $devices | Where-Object { $_.FriendlyName -match 'camera|webcam|uvc' } | Select-Object -First 1 "
        "}; "
    )


def _camera_device_status():
    command = _camera_device_selector_script() + "if ($item) { Write-Output $item.Status } else { Write-Output 'UNKNOWN' }"
    ok, output = _run_powershell(command)
    if not ok:
        return None
    value = (output or "").strip().upper()
    if value == "OK":
        return "on"
    if value in {"ERROR", "UNKNOWN", "DEGRADED"}:
        return "off"
    return None


def _camera_privacy_status():
    command = (
        "$paths=@('HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam',"
        "'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam'); "
        "$value=''; "
        "foreach($p in $paths){ "
        "if(Test-Path $p){ "
        "$entry=Get-ItemProperty -Path $p -Name Value -ErrorAction SilentlyContinue; "
        "if($entry -and $entry.Value){ $value=$entry.Value; break } "
        "} "
        "}; "
        "if(-not $value){ Write-Output 'UNKNOWN' } else { Write-Output $value }"
    )
    ok, output = _run_powershell(command)
    if not ok:
        return None
    value = (output or "").strip().lower()
    if value == "deny":
        return "off"
    if value == "allow":
        return "on"
    return None


def _set_camera_privacy_state(enable):
    value = "Allow" if enable else "Deny"
    command = (
        "$base='HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam'; "
        "if(-not (Test-Path $base)){ New-Item -Path $base -Force | Out-Null }; "
        "$targets = @($base); "
        "$directChildren = Get-ChildItem -Path $base -ErrorAction SilentlyContinue; "
        "foreach($child in $directChildren){ $targets += $child.PSPath }; "
        "$np = Join-Path $base 'NonPackaged'; "
        "if(Test-Path $np){ "
        "$targets += $np; "
        "$npChildren = Get-ChildItem -Path $np -ErrorAction SilentlyContinue; "
        "foreach($child in $npChildren){ $targets += $child.PSPath } "
        "}; "
        f"foreach($t in $targets){{ try{{ Set-ItemProperty -Path $t -Name Value -Value '{value}' -Force -ErrorAction Stop }}catch{{}} }}; "
        "Write-Output 'OK'"
    )
    return _run_powershell(command)


def _camera_effective_status():
    privacy_status = _camera_privacy_status()
    device_status = _camera_device_status()
    if privacy_status == "off":
        return "off"
    if device_status in {"on", "off"}:
        return device_status
    if privacy_status == "on":
        return "on"
    return None


def _set_camera_device_state(enable):
    action = "Enable-PnpDevice" if enable else "Disable-PnpDevice"
    command = (
        _camera_device_selector_script()
        + "if (-not $item) { Write-Output 'NOT_FOUND'; exit 3 }; "
        + f"{action} -InstanceId $item.InstanceId -Confirm:$false -ErrorAction Stop"
    )
    return _run_powershell(command)


def _open_camera_app():
    try:
        os.system("start microsoft.windows.camera:")
        return True
    except Exception:
        return False


def _close_camera_app():
    try:
        subprocess.run(
            ["taskkill", "/IM", "WindowsCamera.exe", "/F"],
            capture_output=True,
            text=True,
            timeout=4,
        )
        return True
    except Exception:
        return False


def _microphone_device_selector_script():
    return (
        "$item = Get-PnpDevice -Class AudioEndpoint -ErrorAction SilentlyContinue | "
        "Where-Object { $_.FriendlyName -and $_.FriendlyName -match 'microphone|mic' } | Select-Object -First 1; "
        "if (-not $item) { "
        "$item = Get-PnpDevice -ErrorAction SilentlyContinue | "
        "Where-Object { $_.FriendlyName -and $_.FriendlyName -match 'microphone|mic' } | Select-Object -First 1 "
        "}; "
    )


def _microphone_device_status():
    command = _microphone_device_selector_script() + "if ($item) { Write-Output $item.Status } else { Write-Output 'UNKNOWN' }"
    ok, output = _run_powershell(command)
    if not ok:
        return None
    value = (output or "").strip().upper()
    if value == "OK":
        return "on"
    if value in {"ERROR", "UNKNOWN", "DEGRADED"}:
        return "off"
    return None


def _set_microphone_device_state(enable):
    action = "Enable-PnpDevice" if enable else "Disable-PnpDevice"
    command = (
        _microphone_device_selector_script()
        + "if (-not $item) { Write-Output 'NOT_FOUND'; exit 3 }; "
        + f"{action} -InstanceId $item.InstanceId -Confirm:$false -ErrorAction Stop"
    )
    return _run_powershell(command)


def _get_do_not_disturb_state():
    command = (
        "$path='HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings'; "
        "if (-not (Test-Path $path)) { Write-Output 'UNKNOWN'; exit 0 }; "
        "$item = Get-ItemProperty -Path $path -Name NOC_GLOBAL_SETTING_TOASTS_ENABLED -ErrorAction SilentlyContinue; "
        "if ($null -eq $item) { Write-Output 'UNKNOWN' } else { Write-Output $item.NOC_GLOBAL_SETTING_TOASTS_ENABLED }"
    )
    ok, output = _run_powershell(command)
    if not ok:
        return None
    text = (output or "").strip().upper()
    if text == "0":
        return "on"
    if text == "1":
        return "off"
    return None


def _set_do_not_disturb_state(enable):
    value = 0 if enable else 1
    command = (
        "$path='HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings'; "
        "if (-not (Test-Path $path)) { New-Item -Path $path -Force | Out-Null }; "
        f"Set-ItemProperty -Path $path -Name NOC_GLOBAL_SETTING_TOASTS_ENABLED -Type DWord -Value {value} -Force; "
        "Write-Output 'OK'"
    )
    return _run_powershell(command)


def _confirm_state(reader, target, attempts=3, delay=0.35):
    for _ in range(max(1, int(attempts))):
        try:
            current = reader()
        except Exception:
            current = None
        if current == target:
            return True
        time.sleep(max(0.05, float(delay)))
    return False


def _admin_relaunch_reply(feature_label):
    relaunch_message = relaunch_assistant_as_admin()
    speak(f"Direct {feature_label} control needs administrator access. {relaunch_message}")


_QUICK_SETTINGS_TILE_LAYOUT = {
    "wifi": (0, 0),
    "bluetooth": (0, 1),
    "airplane_mode": (0, 2),
    "energy_saver": (1, 0),
    "night_light": (1, 1),
    "mobile_hotspot": (1, 2),
    "accessibility": (2, 0),
    "nearby_sharing": (2, 1),
    "live_captions": (2, 2),
    "cast": (3, 0),
    "project": (3, 1),
}


def _toggle_quick_settings_named_tile(tile_key):
    position = _QUICK_SETTINGS_TILE_LAYOUT.get(tile_key)
    if not position:
        return False

    row_offset, column_offset = position

    def _attempt(sequence):
        try:
            pyautogui.hotkey("win", "a")
            time.sleep(0.6)

            for step in sequence:
                if step == "tab":
                    pyautogui.press("tab")
                elif step == "shift_tab":
                    pyautogui.hotkey("shift", "tab")
                elif step == "home":
                    pyautogui.press("home")
                time.sleep(0.08)

            for _ in range(row_offset):
                pyautogui.press("down")
                time.sleep(0.06)

            for _ in range(column_offset):
                pyautogui.press("right")
                time.sleep(0.06)

            pyautogui.press("space")
            time.sleep(0.25)
            pyautogui.press("esc")
            return True
        except Exception:
            try:
                pyautogui.press("esc")
            except Exception:
                pass
            return False

    navigation_sequences = [
        ["home"],
        ["tab", "home"],
        ["tab", "tab", "home"],
        ["shift_tab", "home"],
    ]
    for sequence in navigation_sequences:
        if _attempt(sequence):
            return True
    return False


def _toggle_quick_settings_tile(tile_names):
    names = " ".join(str(name or "").lower() for name in tile_names)
    if "bluetooth" in names:
        tile_key = "bluetooth"
    elif "airplane" in names or "flight" in names:
        tile_key = "airplane_mode"
    elif "energy" in names or "battery saver" in names or "power saver" in names:
        tile_key = "energy_saver"
    elif "night" in names or "blue light" in names:
        tile_key = "night_light"
    elif "accessibility" in names:
        tile_key = "accessibility"
    elif "nearby sharing" in names or "nearby share" in names:
        tile_key = "nearby_sharing"
    elif "live captions" in names or "caption" in names:
        tile_key = "live_captions"
    elif "cast" in names:
        tile_key = "cast"
    elif "project" in names or "second screen" in names or "projection" in names:
        tile_key = "project"
    elif "hotspot" in names:
        tile_key = "mobile_hotspot"
    elif any(token in names for token in ["wi-fi", "wifi", "wireless"]):
        tile_key = "wifi"
    else:
        tile_key = None

    if not tile_key:
        return False

    return _toggle_quick_settings_named_tile(tile_key)


def handle_wifi(command):
    cmd = " ".join((command or "").lower().split())
    cmd = cmd.replace("wi-fi", "wifi").replace("wi fi", "wifi")
    if "wifi" not in cmd and "wi fi" not in cmd and "wireless" not in cmd:
        return False

    if any(phrase in cmd for phrase in ["wifi status", "wi fi status", "wireless status", "is wifi on"]):
        status = _wifi_status_text()
        if status == "on":
            speak("Wi-Fi is on.")
        elif status == "off":
            speak("Wi-Fi is off.")
        else:
            _open_settings("ms-settings:network-wifi", "Wi-Fi settings")
        return True

    if any(phrase in cmd for phrase in ["turn on wifi", "enable wifi", "wifi on", "switch on wifi"]):
        status_before = _wifi_status_text()
        if status_before == "on":
            speak("Wi-Fi is already on.")
            return True

        ok, message = _set_wifi_state(True)
        if ok and _confirm_state(_wifi_status_text, "on"):
            speak("Wi-Fi turned on.")
            return True
        if ok:
            ok_retry, _ = _set_wifi_state(True)
            if ok_retry and _confirm_state(_wifi_status_text, "on"):
                speak("Wi-Fi turned on.")
                return True

        if _is_permission_error(message) and not is_running_as_admin():
            if _toggle_quick_settings_tile(["wi-fi"]):
                if _confirm_state(_wifi_status_text, "on", attempts=2, delay=0.4):
                    speak("I toggled Wi-Fi from quick settings.")
                else:
                    speak("I toggled Wi-Fi from quick settings. If needed, say Wi-Fi on once more.")
                return True
            _admin_relaunch_reply("Wi-Fi")
            return True
        speak("I could not turn on Wi-Fi automatically right now.")
        return True

    if any(phrase in cmd for phrase in ["turn off wifi", "disable wifi", "wifi off", "switch off wifi"]):
        status_before = _wifi_status_text()
        if status_before == "off":
            speak("Wi-Fi is already off.")
            return True

        ok, message = _set_wifi_state(False)
        if ok and _confirm_state(_wifi_status_text, "off"):
            speak("Wi-Fi turned off.")
            return True
        if ok:
            ok_retry, _ = _set_wifi_state(False)
            if ok_retry and _confirm_state(_wifi_status_text, "off"):
                speak("Wi-Fi turned off.")
                return True

        if _is_permission_error(message) and not is_running_as_admin():
            if _toggle_quick_settings_tile(["wi-fi"]):
                if _confirm_state(_wifi_status_text, "off", attempts=2, delay=0.4):
                    speak("I toggled Wi-Fi from quick settings.")
                else:
                    speak("I toggled Wi-Fi from quick settings.")
                return True
            _admin_relaunch_reply("Wi-Fi")
            return True
        speak("I could not turn off Wi-Fi automatically right now.")
        return True

    _open_settings("ms-settings:network-wifi", "Wi-Fi settings")
    return True


def handle_bluetooth(command):
    cmd = " ".join((command or "").lower().split())
    cmd = (
        cmd.replace("blue tooth", "bluetooth")
        .replace("blutooth", "bluetooth")
        .replace("blurtooth", "bluetooth")
    )
    if "bluetooth" not in cmd:
        return False

    if any(phrase in cmd for phrase in ["bluetooth status", "is bluetooth on"]):
        status = _bluetooth_adapter_status() or _bluetooth_service_status()
        if status == "on":
            speak("Bluetooth is on.")
        elif status == "off":
            speak("Bluetooth is off.")
        else:
            _open_settings("ms-settings:bluetooth", "Bluetooth settings")
        return True

    if any(phrase in cmd for phrase in ["turn on bluetooth", "enable bluetooth", "bluetooth on"]):
        status_before = _bluetooth_adapter_status() or _bluetooth_service_status()
        if status_before == "on":
            speak("Bluetooth is already on.")
            return True

        ok, message = _set_bluetooth_radio_state(True)
        if ok and _confirm_state(lambda: _bluetooth_adapter_status() or _bluetooth_service_status(), "on"):
            speak("Bluetooth turned on.")
            return True
        if ok:
            ok_retry, _ = _set_bluetooth_radio_state(True)
            if ok_retry and _confirm_state(lambda: _bluetooth_adapter_status() or _bluetooth_service_status(), "on"):
                speak("Bluetooth turned on.")
                return True
        if "not_found" in (message or "").lower():
            speak("I could not find a controllable Bluetooth adapter on this device.")
            return True

        if _is_permission_error(message) and not is_running_as_admin():
            if _toggle_quick_settings_tile(["bluetooth"]):
                if _confirm_state(lambda: _bluetooth_adapter_status() or _bluetooth_service_status(), "on", attempts=2, delay=0.4):
                    speak("I toggled Bluetooth from quick settings.")
                else:
                    speak("I toggled Bluetooth from quick settings.")
                return True
            _admin_relaunch_reply("Bluetooth")
            return True

        ok, _message = _set_bluetooth_service(True)
        if ok:
            speak("Bluetooth support service started, but adapter state may still depend on Windows policy.")
            return True

        speak("I could not turn on Bluetooth automatically right now.")
        return True

    if any(phrase in cmd for phrase in ["turn off bluetooth", "disable bluetooth", "bluetooth off"]):
        status_before = _bluetooth_adapter_status() or _bluetooth_service_status()
        if status_before == "off":
            speak("Bluetooth is already off.")
            return True

        ok, message = _set_bluetooth_radio_state(False)
        if ok and _confirm_state(lambda: _bluetooth_adapter_status() or _bluetooth_service_status(), "off"):
            speak("Bluetooth turned off.")
            return True
        if ok:
            ok_retry, _ = _set_bluetooth_radio_state(False)
            if ok_retry and _confirm_state(lambda: _bluetooth_adapter_status() or _bluetooth_service_status(), "off"):
                speak("Bluetooth turned off.")
                return True
        if "not_found" in (message or "").lower():
            speak("I could not find a controllable Bluetooth adapter on this device.")
            return True

        if _is_permission_error(message) and not is_running_as_admin():
            if _toggle_quick_settings_tile(["bluetooth"]):
                if _confirm_state(lambda: _bluetooth_adapter_status() or _bluetooth_service_status(), "off", attempts=2, delay=0.4):
                    speak("I toggled Bluetooth from quick settings.")
                else:
                    speak("I toggled Bluetooth from quick settings.")
                return True
            _admin_relaunch_reply("Bluetooth")
            return True

        ok, _message = _set_bluetooth_service(False)
        if ok:
            speak("Bluetooth support service stopped, but adapter state may still depend on Windows policy.")
            return True

        speak("I could not turn off Bluetooth automatically right now.")
        return True

    _open_settings("ms-settings:bluetooth", "Bluetooth settings")
    return True


def handle_airplane(command):
    cmd = " ".join((command or "").lower().split())
    if "airplane" in cmd or "flight mode" in cmd:
        if any(phrase in cmd for phrase in ["airplane mode status", "flight mode status", "is airplane mode on"]):
            speak("Airplane mode state check is limited on Windows APIs. Say airplane mode on or off and I will toggle it.")
            return True

        if any(phrase in cmd for phrase in ["turn on airplane mode", "enable airplane mode", "airplane mode on"]):
            if _toggle_quick_settings_tile(["airplane mode"]):
                speak("I toggled airplane mode from quick settings.")
                return True
            speak("I could not toggle airplane mode automatically. Opening Airplane mode settings.")
            os.system("start ms-settings:network-airplanemode")
            return True
        if any(phrase in cmd for phrase in ["turn off airplane mode", "disable airplane mode", "airplane mode off"]):
            if _toggle_quick_settings_tile(["airplane mode"]):
                speak("I toggled airplane mode from quick settings.")
                return True
            speak("I could not toggle airplane mode automatically. Opening Airplane mode settings.")
            os.system("start ms-settings:network-airplanemode")
            return True
        speak("Opening Airplane mode settings")
        os.system("start ms-settings:network-airplanemode")
        return True
    return False


def handle_focus_assist(command):
    cmd = " ".join((command or "").lower().split())
    if not any(token in cmd for token in ["focus assist", "do not disturb", "dnd", "quiet hours"]):
        return False

    if any(phrase in cmd for phrase in ["status", "is focus assist", "is do not disturb"]):
        status = _get_do_not_disturb_state()
        if status == "on":
            speak("Do not disturb is on.")
        elif status == "off":
            speak("Do not disturb is off.")
        else:
            speak("I could not verify do not disturb state right now.")
        return True

    if any(phrase in cmd for phrase in ["turn on", "switch on", "enable", "focus assist on", "dnd on"]):
        ok, _message = _set_do_not_disturb_state(True)
        if ok and _confirm_state(_get_do_not_disturb_state, "on", attempts=2, delay=0.25):
            speak("Do not disturb turned on.")
            return True
        speak("I could not turn on do not disturb automatically. Opening Focus Assist settings.")
        _open_settings("ms-settings:quiethours", "Focus Assist settings")
        return True

    if any(phrase in cmd for phrase in ["turn off", "switch off", "disable", "focus assist off", "dnd off"]):
        ok, _message = _set_do_not_disturb_state(False)
        if ok and _confirm_state(_get_do_not_disturb_state, "off", attempts=2, delay=0.25):
            speak("Do not disturb turned off.")
            return True
        speak("I could not turn off do not disturb automatically. Opening Focus Assist settings.")
        _open_settings("ms-settings:quiethours", "Focus Assist settings")
        return True

    _open_settings("ms-settings:quiethours", "Focus Assist settings")
    return True


def handle_camera_controls(command):
    cmd = " ".join((command or "").lower().split())
    if "camera" not in cmd:
        return False

    # Keep object-detection commands with the vision pipeline.
    if any(token in cmd for token in ["object detection", "visible on camera", "on camera", "scan camera"]):
        return False

    if any(phrase in cmd for phrase in ["camera status", "is camera on"]):
        status = _camera_effective_status()
        if status == "on":
            speak("Camera is on.")
        elif status == "off":
            speak("Camera is off.")
        else:
            speak("I could not verify camera state right now.")
        return True

    if any(phrase in cmd for phrase in ["turn on camera", "enable camera", "camera on", "unblock camera"]):
        status_before = _camera_effective_status()
        if status_before == "on":
            if _open_camera_app():
                speak("Camera is already on. Opening Camera app.")
            else:
                speak("Camera is already on.")
            return True

        _set_camera_privacy_state(True)
        ok, message = _set_camera_device_state(True)
        if ok and _confirm_state(_camera_effective_status, "on"):
            if _open_camera_app():
                speak("Camera turned on and Camera app opened.")
            else:
                speak("Camera turned on.")
            return True
        if ok:
            ok_retry, _ = _set_camera_device_state(True)
            if ok_retry and _confirm_state(_camera_effective_status, "on"):
                if _open_camera_app():
                    speak("Camera turned on and Camera app opened.")
                else:
                    speak("Camera turned on.")
                return True
        lower_message = (message or "").lower()
        if "generic failure" in lower_message or "0x80041001" in lower_message:
            ok_privacy, _ = _set_camera_privacy_state(True)
            if ok_privacy and _confirm_state(_camera_effective_status, "on", attempts=2, delay=0.3):
                if _open_camera_app():
                    speak("Camera access turned on and Camera app opened.")
                else:
                    speak("Camera access turned on.")
                return True
        if "not_found" in (message or "").lower():
            speak("I could not find a controllable camera device.")
            return True
        if _is_permission_error(message) and not is_running_as_admin():
            _admin_relaunch_reply("camera")
            return True
        speak("I could not turn on camera automatically right now.")
        return True

    if any(phrase in cmd for phrase in ["turn off camera", "disable camera", "camera off", "block camera"]):
        status_before = _camera_effective_status()
        if status_before == "off":
            speak("Camera is already off.")
            return True

        _close_camera_app()
        time.sleep(0.2)
        ok, message = _set_camera_device_state(False)
        if ok and _confirm_state(_camera_effective_status, "off"):
            speak("Camera turned off.")
            return True
        if ok:
            ok_retry, _ = _set_camera_device_state(False)
            if ok_retry and _confirm_state(_camera_effective_status, "off"):
                speak("Camera turned off.")
                return True
        lower_message = (message or "").lower()
        if "generic failure" in lower_message or "0x80041001" in lower_message:
            ok_privacy, _ = _set_camera_privacy_state(False)
            if ok_privacy and _confirm_state(_camera_effective_status, "off", attempts=2, delay=0.3):
                speak("Camera access turned off.")
                return True
        if "not_found" in (message or "").lower():
            speak("I could not find a controllable camera device.")
            return True
        if _is_permission_error(message) and not is_running_as_admin():
            _admin_relaunch_reply("camera")
            return True
        speak("I could not turn off camera automatically right now.")
        return True

    _open_settings("ms-settings:privacy-webcam", "Camera privacy settings")
    return True


def handle_microphone_controls(command):
    cmd = " ".join((command or "").lower().split())
    if not ("microphone" in cmd or re.search(r"\bmic\b", cmd)):
        return False

    if any(phrase in cmd for phrase in ["microphone status", "mic status", "is microphone on"]):
        status = _microphone_device_status()
        if status == "on":
            speak("Microphone is on.")
        elif status == "off":
            speak("Microphone is off.")
        else:
            speak("I could not verify microphone state right now.")
        return True

    if any(
        phrase in cmd
        for phrase in ["unmute microphone", "unmute mic", "turn on microphone", "enable microphone", "microphone on", "mic on"]
    ):
        ok, message = _set_microphone_device_state(True)
        if ok and _confirm_state(_microphone_device_status, "on"):
            speak("Microphone unmuted and enabled.")
            return True
        if ok:
            ok_retry, _ = _set_microphone_device_state(True)
            if ok_retry and _confirm_state(_microphone_device_status, "on"):
                speak("Microphone unmuted and enabled.")
                return True
        if "not_found" in (message or "").lower():
            speak("I could not find a controllable microphone device.")
            return True
        if _is_permission_error(message) and not is_running_as_admin():
            _admin_relaunch_reply("microphone")
            return True
        speak("I could not enable microphone automatically right now.")
        return True

    if any(
        phrase in cmd
        for phrase in ["mute microphone", "mute mic", "turn off microphone", "disable microphone", "microphone off", "mic off"]
    ):
        ok, message = _set_microphone_device_state(False)
        if ok and _confirm_state(_microphone_device_status, "off"):
            speak("Microphone muted by disabling the input device.")
            return True
        if ok:
            ok_retry, _ = _set_microphone_device_state(False)
            if ok_retry and _confirm_state(_microphone_device_status, "off"):
                speak("Microphone muted by disabling the input device.")
                return True
        if "not_found" in (message or "").lower():
            speak("I could not find a controllable microphone device.")
            return True
        if _is_permission_error(message) and not is_running_as_admin():
            _admin_relaunch_reply("microphone")
            return True
        speak("I could not mute microphone automatically right now.")
        return True

    _open_settings("ms-settings:privacy-microphone", "Microphone privacy settings")
    return True


def handle_quick_settings_controls(command):
    cmd = " ".join((command or "").lower().split())
    cmd = (
        cmd.replace("wi-fi", "wifi")
        .replace("wi fi", "wifi")
        .replace("blue tooth", "bluetooth")
        .replace("blutooth", "bluetooth")
        .replace("blurtooth", "bluetooth")
    )

    tile_aliases = {
        "energy_saver": ["energy saver", "battery saver", "power saver"],
        "night_light": ["night light", "blue light", "night mode"],
        "mobile_hotspot": ["mobile hotspot", "wifi hotspot", "hotspot"],
        "accessibility": ["accessibility", "accessibility menu"],
        "nearby_sharing": ["nearby sharing", "nearby share"],
        "live_captions": ["live captions", "live caption", "captions"],
        "cast": ["cast", "cast screen", "screen cast"],
        "project": ["project screen", "second screen", "projection mode", "project display"],
    }
    tile_labels = {
        "energy_saver": "energy saver",
        "night_light": "night light",
        "mobile_hotspot": "mobile hotspot",
        "accessibility": "accessibility",
        "nearby_sharing": "nearby sharing",
        "live_captions": "live captions",
        "cast": "cast",
        "project": "project",
    }
    settings_uris = {
        "energy_saver": "ms-settings:batterysaver",
        "night_light": "ms-settings:nightlight",
        "mobile_hotspot": "ms-settings:network-mobilehotspot",
        "accessibility": "ms-settings:easeofaccess",
        "nearby_sharing": "ms-settings:nearbysharing",
        "live_captions": "ms-settings:easeofaccess-closedcaptioning",
        "cast": "ms-settings:display",
        "project": "ms-settings:display",
    }
    toggle_tiles = {"energy_saver", "night_light", "mobile_hotspot", "nearby_sharing", "live_captions"}
    action_tiles = {"accessibility", "cast", "project"}

    def _alias_match(alias):
        token = alias.strip().lower()
        if not token:
            return False
        if " " in token:
            return token in cmd
        return bool(re.search(rf"\b{re.escape(token)}\b", cmd))

    selected_tile = None
    for tile_key, aliases in tile_aliases.items():
        if any(_alias_match(alias) for alias in aliases):
            selected_tile = tile_key
            break

    if not selected_tile:
        return False

    on_intent = any(phrase in cmd for phrase in ["turn on", "switch on", "enable"]) or bool(
        re.search(r"\bon\b", cmd)
    )
    off_intent = any(phrase in cmd for phrase in ["turn off", "switch off", "disable"]) or bool(
        re.search(r"\boff\b", cmd)
    )
    status_intent = any(phrase in cmd for phrase in ["status", "is ", "are ", "check"])

    if status_intent and not on_intent and not off_intent and selected_tile in toggle_tiles:
        speak(
            f"{tile_labels[selected_tile].title()} state check is limited by Windows APIs. "
            f"Say {tile_labels[selected_tile]} on or {tile_labels[selected_tile]} off and I will toggle it."
        )
        return True

    if selected_tile in action_tiles:
        if _toggle_quick_settings_named_tile(selected_tile):
            speak(f"I opened {tile_labels[selected_tile]} from quick settings.")
            return True
        _open_settings(settings_uris[selected_tile], f"{tile_labels[selected_tile]} settings")
        return True

    if on_intent or off_intent:
        if _toggle_quick_settings_named_tile(selected_tile):
            speak(f"I toggled {tile_labels[selected_tile]} from quick settings.")
            return True
        speak(f"I could not toggle {tile_labels[selected_tile]} automatically right now.")
        return True

    _open_settings(settings_uris[selected_tile], f"{tile_labels[selected_tile]} settings")
    return True


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


def get_storage_report():
    try:
        usage = psutil.disk_usage(os.path.abspath(os.sep))
    except Exception:
        return "I could not read the current storage usage."

    free_gb = usage.free / (1024 ** 3)
    total_gb = usage.total / (1024 ** 3)
    used_percent = usage.percent
    return f"Storage status: {used_percent}% used, {free_gb:.1f} GB free out of {total_gb:.1f} GB."


def get_cleanup_suggestion():
    try:
        usage = psutil.disk_usage(os.path.abspath(os.sep))
    except Exception:
        return "I could not inspect the storage right now."

    percent = usage.percent
    if percent >= 90:
        return "Storage is very high. Start with Downloads, large videos, installer files, and temporary screenshots."
    if percent >= 75:
        return "Storage is getting tight. Cleaning Downloads, duplicate media, and unused virtual environments would help."
    return "Storage looks comfortable right now. A light cleanup of Downloads and old exports should be enough."


def get_motivation_line():
    lines = [
        "You are already building something most people only talk about. Keep shipping.",
        "Small clean progress today is enough. Momentum matters more than drama.",
        "You do not need a perfect day, just one more finished step.",
        "Consistency is making this assistant stronger every round. Keep going.",
    ]
    return random.choice(lines)
