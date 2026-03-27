import datetime
import os

from modules.dashboard_module import build_today_agenda
from modules.event_module import get_event_data
from modules.task_module import get_task_data


EXPORT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "exports",
)


def export_productivity_summary(_command=None):
    os.makedirs(EXPORT_DIR, exist_ok=True)

    now = datetime.datetime.now()
    filename = f"summary_{now.strftime('%Y%m%d_%H%M%S')}.txt"
    export_path = os.path.join(EXPORT_DIR, filename)

    task_data = get_task_data()
    event_data = get_event_data()

    pending_tasks = [
        task.get("title", "Untitled task")
        for task in task_data.get("tasks", [])
        if not task.get("completed")
    ]
    reminders = [
        reminder.get("title", "Untitled reminder")
        for reminder in task_data.get("reminders", [])
    ]
    events = sorted(
        event_data.get("events", []),
        key=lambda event: (event.get("date") or "9999-12-31", event.get("time") or "23:59"),
    )

    lines = [
        "Grandpa Assistant Productivity Summary",
        f"Generated: {now.strftime('%d %B %Y %I:%M %p')}",
        "",
        "Today Agenda",
        build_today_agenda(),
        "",
        f"Pending Tasks ({len(pending_tasks)})",
    ]

    if pending_tasks:
        lines.extend(f"- {title}" for title in pending_tasks)
    else:
        lines.append("- None")

    lines.append("")
    lines.append(f"Reminders ({len(reminders)})")
    if reminders:
        lines.extend(f"- {title}" for title in reminders[:20])
    else:
        lines.append("- None")

    lines.append("")
    lines.append(f"Events ({len(events)})")
    if events:
        for event in events[:20]:
            title = event.get("title", "Untitled event")
            date_text = event.get("date") or "No date"
            time_text = event.get("time") or "No time"
            lines.append(f"- {title} | {date_text} | {time_text}")
    else:
        lines.append("- None")

    with open(export_path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))

    return f"Summary exported to {export_path}"
