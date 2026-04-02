import shutil

import psutil


def _battery_text():
    battery = psutil.sensors_battery()
    if battery is None:
        return "Battery information is not available."

    status = "charging" if battery.power_plugged else "not charging"
    return f"Battery is at {battery.percent}% and {status}."


def _memory_text():
    memory = psutil.virtual_memory()
    used_gb = memory.used / (1024 ** 3)
    total_gb = memory.total / (1024 ** 3)
    return f"RAM usage is {memory.percent} percent. Used {used_gb:.1f} GB out of {total_gb:.1f} GB."


def _cpu_text():
    cpu_percent = psutil.cpu_percent(interval=0.4)
    return f"CPU usage is currently {cpu_percent} percent."


def _disk_text():
    disk = shutil.disk_usage("/")
    used_gb = disk.used / (1024 ** 3)
    total_gb = disk.total / (1024 ** 3)
    free_gb = disk.free / (1024 ** 3)
    used_percent = (disk.used / disk.total) * 100 if disk.total else 0
    return (
        f"Disk usage is {used_percent:.0f} percent. "
        f"Used {used_gb:.1f} GB, free {free_gb:.1f} GB, total {total_gb:.1f} GB."
    )


def get_system_status():
    return " ".join([
        _cpu_text(),
        _memory_text(),
        _disk_text(),
        _battery_text(),
    ])


def get_cpu_status():
    return _cpu_text()


def get_ram_status():
    return _memory_text()


def get_disk_status():
    return _disk_text()


def get_battery_status():
    return _battery_text()
