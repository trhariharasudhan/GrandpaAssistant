import datetime


name = "time"
description = "Returns the current local time with optional label input."


def execute(input_data):
    label = str(input_data or "").strip()
    now = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    return {
        "ok": True,
        "plugin": name,
        "label": label,
        "result": f"{label + ': ' if label else ''}{now}",
    }
