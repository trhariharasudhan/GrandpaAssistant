import datetime
import os

from productivity.dashboard_module import build_daily_recap, build_today_agenda
from productivity.event_module import get_event_data
from productivity.task_module import get_task_data


EXPORT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data",
    "exports",
)


def _build_summary_lines():
    now = datetime.datetime.now()

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

    return now, lines


def _build_recap_lines():
    now = datetime.datetime.now()
    recap_text = build_daily_recap()
    lines = [
        "Grandpa Assistant Daily Recap",
        f"Generated: {now.strftime('%d %B %Y %I:%M %p')}",
        "",
    ]
    lines.extend(recap_text.splitlines() or [recap_text])
    return now, lines


def _escape_pdf_text(value):
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _write_basic_pdf(path, lines):
    page_width = 595
    page_height = 842
    x = 50
    y = 790
    line_height = 16
    font_size = 11

    content_lines = ["BT", f"/F1 {font_size} Tf"]
    current_y = y
    for raw_line in lines:
        text = _escape_pdf_text(raw_line[:110])
        content_lines.append(f"1 0 0 1 {x} {current_y} Tm ({text}) Tj")
        current_y -= line_height
        if current_y < 50:
            break
    content_lines.append("ET")
    content = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objects.append(
        f"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n".encode(
            "ascii"
        )
    )
    objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
    objects.append(
        f"5 0 obj << /Length {len(content)} >> stream\n".encode("ascii")
        + content
        + b"\nendstream endobj\n"
    )

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode(
            "ascii"
        )
    )

    with open(path, "wb") as file:
        file.write(pdf)


def export_productivity_summary(_command=None):
    os.makedirs(EXPORT_DIR, exist_ok=True)

    now, lines = _build_summary_lines()
    filename = f"summary_{now.strftime('%Y%m%d_%H%M%S')}.txt"
    export_path = os.path.join(EXPORT_DIR, filename)

    with open(export_path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))

    return f"Summary exported to {export_path}"


def export_productivity_summary_pdf(_command=None):
    os.makedirs(EXPORT_DIR, exist_ok=True)

    now, lines = _build_summary_lines()
    filename = f"summary_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
    export_path = os.path.join(EXPORT_DIR, filename)

    _write_basic_pdf(export_path, lines)
    return f"PDF summary exported to {export_path}"


def export_daily_recap_summary(_command=None):
    os.makedirs(EXPORT_DIR, exist_ok=True)

    now, lines = _build_recap_lines()
    filename = f"daily_recap_{now.strftime('%Y%m%d_%H%M%S')}.txt"
    export_path = os.path.join(EXPORT_DIR, filename)

    with open(export_path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))

    return f"Daily recap exported to {export_path}"


def export_daily_recap_pdf(_command=None):
    os.makedirs(EXPORT_DIR, exist_ok=True)

    now, lines = _build_recap_lines()
    filename = f"daily_recap_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
    export_path = os.path.join(EXPORT_DIR, filename)

    _write_basic_pdf(export_path, lines)
    return f"Daily recap PDF exported to {export_path}"
