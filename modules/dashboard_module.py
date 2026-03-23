from modules.briefing_module import build_brief_details, build_due_reminder_alert
from modules.system_module import get_battery_info
from modules.task_module import get_task_data
from modules.weather_module import get_weather_report


def build_dashboard_report():
    parts = [build_brief_details()]

    battery_info = get_battery_info()
    if battery_info:
        parts.append(battery_info + ".")

    weather_info = get_weather_report("weather")
    if weather_info and "could not fetch weather" not in weather_info.lower():
        parts.append(weather_info)

    urgent_info = build_due_reminder_alert()
    if urgent_info and urgent_info != "No urgent reminders right now.":
        parts.append(urgent_info)

    data = get_task_data()
    pending_tasks = [task for task in data.get("tasks", []) if not task.get("completed")]
    reminders = data.get("reminders", [])

    if pending_tasks:
        top_tasks = ", ".join(task.get("title", "Untitled task") for task in pending_tasks[:3])
        parts.append(f"Top pending tasks: {top_tasks}.")

    if reminders:
        top_reminders = ", ".join(
            reminder.get("title", "Untitled reminder") for reminder in reminders[:3]
        )
        parts.append(f"Recent reminders: {top_reminders}.")

    return " ".join(part.strip() for part in parts if part)
