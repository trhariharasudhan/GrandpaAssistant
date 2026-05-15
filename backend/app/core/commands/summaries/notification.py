from __future__ import annotations

from utils.config import get_setting


def notification_status_summary() -> str:
    reminder_monitor = get_setting("notifications.reminder_monitor_enabled", True)
    reminder_interval = get_setting("notifications.reminder_check_interval_minutes", 15)
    event_monitor = get_setting("notifications.event_monitor_enabled", True)
    event_interval = get_setting("notifications.event_check_interval_minutes", 15)
    morning_brief = get_setting("notifications.morning_brief_automation_enabled", False)
    morning_time = get_setting("notifications.morning_brief_time", "08:00")
    night_summary = get_setting("notifications.night_summary_export_enabled", False)
    night_time = get_setting("notifications.night_summary_time", "21:00")
    weekend_automation = get_setting("notifications.weekend_automation_enabled", True)
    weekdays_only = get_setting("notifications.automation_weekdays_only", False)
    return (
        f"Reminder monitor is {'on' if reminder_monitor else 'off'} every {reminder_interval} minutes. "
        f"Event monitor is {'on' if event_monitor else 'off'} every {event_interval} minutes. "
        f"Morning brief automation is {'on' if morning_brief else 'off'} at {morning_time}. "
        f"Night summary export is {'on' if night_summary else 'off'} at {night_time}. "
        f"Weekday only automations are {'on' if weekdays_only else 'off'}. "
        f"Weekend automations are {'on' if weekend_automation else 'off'}."
    )


def notification_help_summary() -> str:
    return (
        "Notification summaries can report notification status, popup status, reminder notification status, "
        "and notification history. Sending popups, alerts, and reminder changes still require the existing action commands."
    )


def popup_alert_status_summary() -> str:
    voice_popup = get_setting("voice.desktop_popup_enabled", True)
    whatsapp_popup = get_setting("browser.whatsapp_success_popup_enabled", True)
    health_popup = get_setting("notifications.health_popup_enabled", False)
    health_startup = get_setting("notifications.health_popup_on_startup", False)
    health_interval = get_setting("notifications.health_popup_interval_minutes", 60)
    weather_popup = get_setting("notifications.weather_popup_enabled", False)
    weather_startup = get_setting("notifications.weather_popup_on_startup", False)
    weather_interval = get_setting("notifications.weather_popup_interval_minutes", 120)
    status_popup = get_setting("notifications.status_popup_enabled", False)
    status_startup = get_setting("notifications.status_popup_on_startup", False)
    status_interval = get_setting("notifications.status_popup_interval_minutes", 120)
    brief_popup = get_setting("notifications.brief_popup_enabled", False)
    brief_startup = get_setting("notifications.brief_popup_on_startup", False)
    brief_interval = get_setting("notifications.brief_popup_interval_minutes", 180)
    agenda_popup = get_setting("notifications.agenda_popup_enabled", False)
    agenda_startup = get_setting("notifications.agenda_popup_on_startup", False)
    agenda_interval = get_setting("notifications.agenda_popup_interval_minutes", 60)
    recap_popup = get_setting("notifications.recap_popup_enabled", False)
    recap_startup = get_setting("notifications.recap_popup_on_startup", False)
    recap_interval = get_setting("notifications.recap_popup_interval_minutes", 180)
    popup_timeout = get_setting("notifications.popup_timeout_seconds", 10)
    popup_cooldown = get_setting("notifications.popup_cooldown_seconds", 180)
    return (
        f"Voice desktop popup is {'on' if voice_popup else 'off'}. "
        f"WhatsApp success popup is {'on' if whatsapp_popup else 'off'}. "
        f"Health popup is {'on' if health_popup else 'off'}, startup {'on' if health_startup else 'off'}, interval {health_interval} minutes. "
        f"Weather popup is {'on' if weather_popup else 'off'}, startup {'on' if weather_startup else 'off'}, interval {weather_interval} minutes. "
        f"Status popup is {'on' if status_popup else 'off'}, startup {'on' if status_startup else 'off'}, interval {status_interval} minutes. "
        f"Brief popup is {'on' if brief_popup else 'off'}, startup {'on' if brief_startup else 'off'}, interval {brief_interval} minutes. "
        f"Agenda popup is {'on' if agenda_popup else 'off'}, startup {'on' if agenda_startup else 'off'}, interval {agenda_interval} minutes. "
        f"Recap popup is {'on' if recap_popup else 'off'}, startup {'on' if recap_startup else 'off'}, interval {recap_interval} minutes. "
        f"Popup timeout is {popup_timeout} seconds. Popup cooldown is {popup_cooldown} seconds."
    )


def reminder_notification_summary() -> str:
    reminder_monitor = get_setting("notifications.reminder_monitor_enabled", True)
    reminder_interval = get_setting("notifications.reminder_check_interval_minutes", 15)
    event_monitor = get_setting("notifications.event_monitor_enabled", True)
    event_interval = get_setting("notifications.event_check_interval_minutes", 15)
    return (
        f"Reminder monitor is {'on' if reminder_monitor else 'off'} every {reminder_interval} minutes. "
        f"Event monitor is {'on' if event_monitor else 'off'} every {event_interval} minutes."
    )


def notification_history_summary() -> str:
    return "Notification history is not stored by this backend yet. Use reminder timeline or automation history for read-only related summaries."
