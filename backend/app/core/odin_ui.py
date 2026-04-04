import contextlib
import datetime
import io
import re
import threading
import time
import tkinter as tk
from tkinter import ttk

from brain.memory_engine import get_memory
import core.command_router as command_router_module
from modules.event_module import get_event_data
from modules.google_calendar_module import upcoming_google_calendar_title_lines
from modules.health_module import get_system_status
from modules.notes_module import latest_note
from modules.task_module import get_task_data
from modules.weather_module import get_weather_report
from utils.config import get_setting
from voice.listen import listen
import voice.speak as voice_speak_module


PALETTE = {
    "blue": "#0d6efd",
    "indigo": "#6610f2",
    "purple": "#6f42c1",
    "pink": "#d63384",
    "red": "#dc3545",
    "orange": "#fd7e14",
    "yellow": "#ffc107",
    "green": "#198754",
    "teal": "#20c997",
    "cyan": "#0dcaf0",
    "white": "#fff",
    "gray": "#6c757d",
    "gray_dark": "#343a40",
    "primary": "#6244c5",
    "secondary": "#ffc448",
    "success": "#198754",
    "info": "#0dcaf0",
    "warning": "#ffc107",
    "danger": "#dc3545",
    "light": "#fafafb",
    "dark": "#12141d",
    "surface": "#ffffff",
    "shell": "#eef0fb",
    "border": "#e3e5f4",
    "soft_border": "#ececff",
    "console": "#202434",
    "console_alt": "#29263b",
}


class OdinUI:
    AUTO_CORRECT_MAP = {
        "alot": "a lot",
        "becuase": "because",
        "definately": "definitely",
        "doesnt": "doesn't",
        "dont": "don't",
        "havent": "haven't",
        "hte": "the",
        "iam": "I am",
        "im": "I'm",
        "ive": "I've",
        "idk": "I don't know",
        "msg": "message",
        "pls": "please",
        "plz": "please",
        "realy": "really",
        "recieve": "receive",
        "teh": "the",
        "thx": "thanks",
        "tmrw": "tomorrow",
        "u": "you",
        "ur": "your",
        "wont": "won't",
    }
    COMMAND_TIMEOUT_SECONDS = 25

    def __init__(self, installed_apps, startup_messages=None):
        self.installed_apps = installed_apps
        self.startup_messages = startup_messages or []
        self.root = tk.Tk()
        self.root.title("Grandpa Assistant")
        self.root.geometry("1220x790")
        self.root.minsize(1120, 720)
        self.root.configure(bg="#f7f7ff")

        self.time_var = tk.StringVar()
        self.date_var = tk.StringVar()
        self.input_var = tk.StringVar()
        self.voice_state_var = tk.StringVar(value="")
        self.weather_var = tk.StringVar(value="Weather unavailable")
        self.health_var = tk.StringVar(value="Health unavailable")
        self.activity_var = tk.StringVar(value="Ready")
        self.transcript_var = tk.StringVar(value="")
        self.daily_summary_var = tk.StringVar(value="Assistant is ready.")
        self.next_event_var = tk.StringVar(value="No upcoming events.")
        self.latest_note_var = tk.StringVar(value="No saved notes.")
        self.memory_snapshot_var = tk.StringVar(value="No saved preferences.")
        self.calendar_titles_var = tk.StringVar(value="No Google Calendar titles.")
        self.sidebar_section = "overview"
        self.voice_thread = None
        self.voice_stop_requested = False
        self.command_running = False
        self._real_voice_speak = voice_speak_module.speak
        self.mode_is_voice = False
        self.voice_orb_state = "idle"
        self.voice_orb_phase = 0
        self.text_mode_button = None
        self.voice_mode_button = None
        self.voice_orb_canvas = None
        self.confirm_bar = None
        self.bottom = None
        self.entry = None
        self.sidebar_section_buttons = {}
        self.sidebar_content_frame = None
        self._autocorrect_job = None
        self._autocorrect_updating = False

        self._configure_styles()
        self._build_layout()
        self._update_clock()
        self._refresh_cards()
        self._load_startup_messages()
        self._apply_response_mode()
        self.root.protocol("WM_DELETE_WINDOW", self._close_window)
        self._animate_voice_orb()

    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Odin.TFrame",
            background=PALETTE["light"],
        )
        style.configure(
            "OdinCard.TFrame",
            background=PALETTE["white"],
            borderwidth=0,
        )
        style.configure(
            "Odin.TEntry",
            fieldbackground=PALETTE["white"],
            foreground=PALETTE["dark"],
            borderwidth=0,
            padding=10,
        )

    def _build_layout(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        outer = tk.Frame(self.root, bg="#f7f7ff", padx=14, pady=10)
        outer.grid(sticky="nsew")
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(2, weight=1)

        header = tk.Frame(outer, bg="#f7f7ff")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        logo_wrap = tk.Frame(header, bg="#f7f7ff")
        logo_wrap.grid(row=0, column=0, sticky="w")

        logo = tk.Canvas(
            logo_wrap,
            width=92,
            height=92,
            bg="#f7f7ff",
            highlightthickness=0,
            bd=0,
        )
        logo.pack(side="left")
        self._draw_logo(logo)

        title_wrap = tk.Frame(logo_wrap, bg="#f7f7ff")
        title_wrap.pack(side="left", padx=(12, 0))
        title_row = tk.Frame(title_wrap, bg="#f7f7ff")
        title_row.pack(anchor="w")
        tk.Label(
            title_row,
            text="Grandpa Assistant",
            font=("Segoe UI Semibold", 24),
            fg=PALETTE["dark"],
            bg="#f7f7ff",
        ).pack(side="left")
        voice_row = tk.Frame(title_row, bg="#f7f7ff")
        voice_row.pack(side="left", padx=(16, 0), pady=(0, 0))
        self.mode_label = tk.Label(
            voice_row,
            textvariable=self.voice_state_var,
            font=("Segoe UI Semibold", 10),
            fg=PALETTE["success"],
            bg="#f7f7ff",
        )
        mode_bar = tk.Frame(
            voice_row,
            bg=PALETTE["dark"],
            highlightthickness=0,
            bd=0,
            padx=3,
            pady=3,
        )
        mode_bar.pack(side="left", pady=(2, 0))
        self.text_mode_button = tk.Button(
            mode_bar,
            text="Text",
            command=self._set_text_mode,
            relief="flat",
            bd=0,
            padx=16,
            pady=8,
            font=("Segoe UI Semibold", 10),
            cursor="hand2",
        )
        self.text_mode_button.pack(side="left")
        self.voice_mode_button = tk.Button(
            mode_bar,
            text="Voice",
            command=self._set_voice_mode,
            relief="flat",
            bd=0,
            padx=16,
            pady=8,
            font=("Segoe UI Semibold", 10),
            cursor="hand2",
        )
        self.voice_mode_button.pack(side="left", padx=(4, 0))

        orb_wrap = tk.Frame(voice_row, bg="#f7f7ff")
        orb_wrap.pack(side="left", padx=(16, 0), pady=(2, 0))
        self.voice_orb_canvas = tk.Canvas(
            orb_wrap,
            width=16,
            height=16,
            bg="#f7f7ff",
            highlightthickness=0,
            bd=0,
        )
        self.voice_orb_canvas.pack(side="left")
        tk.Label(
            orb_wrap,
            textvariable=self.activity_var,
            font=("Segoe UI", 10),
            fg=PALETTE["gray"],
            bg="#f7f7ff",
        ).pack(side="left", padx=(6, 0))
        self._draw_voice_orb()

        time_wrap = tk.Frame(header, bg="#f7f7ff")
        time_wrap.grid(row=0, column=1, sticky="e")
        tk.Label(
            time_wrap,
            textvariable=self.time_var,
            font=("Segoe UI Semibold", 26),
            fg=PALETTE["primary"],
            bg="#f7f7ff",
        ).pack(anchor="e")
        tk.Label(
            time_wrap,
            textvariable=self.date_var,
            font=("Segoe UI", 11),
            fg=PALETTE["gray"],
            bg="#f7f7ff",
        ).pack(anchor="e")

        tk.Frame(outer, bg="#ecebfd", height=1).grid(row=1, column=0, sticky="ew", pady=(10, 12))

        content = tk.Frame(outer, bg="#f7f7ff")
        content.grid(row=2, column=0, sticky="nsew")
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        status_wrap = tk.Frame(content, bg="#f7f7ff", width=286)
        status_wrap.grid(row=0, column=0, sticky="nsw", padx=(0, 14))
        status_wrap.grid_propagate(False)
        self._build_status_panel(status_wrap)

        main_shell = tk.Frame(
            content,
            bg="#eef0fb",
            bd=0,
            highlightthickness=1,
            highlightbackground=PALETTE["soft_border"],
        )
        main_shell.grid(row=0, column=1, sticky="nsew")

        main = tk.Frame(main_shell, bg=PALETTE["surface"], bd=0, highlightthickness=0)
        main.pack(fill="both", expand=True, padx=2, pady=2)

        console_wrap = tk.Frame(main, bg=PALETTE["surface"], padx=16, pady=16)
        console_wrap.pack(fill="both", expand=True)
        console_wrap.grid_columnconfigure(0, weight=1)
        console_wrap.grid_rowconfigure(1, weight=1)

        conversation_header = tk.Frame(console_wrap, bg=PALETTE["surface"])
        conversation_header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        conversation_header.grid_columnconfigure(0, weight=1)

        tk.Label(
            conversation_header,
            text="Conversation",
            font=("Segoe UI Semibold", 12),
            fg=PALETTE["dark"],
            bg=PALETTE["surface"],
        ).grid(row=0, column=0, sticky="w")

        tk.Button(
            conversation_header,
            text="Reload",
            command=self._reload_conversation,
            bg=PALETTE["dark"],
            fg=PALETTE["white"],
            activebackground=PALETTE["dark"],
            activeforeground=PALETTE["white"],
            relief="flat",
            bd=0,
            padx=15,
            pady=7,
            font=("Segoe UI Semibold", 9),
            cursor="hand2",
        ).grid(row=0, column=1, sticky="e")

        self.console = tk.Text(
            console_wrap,
            bg=PALETTE["console"],
            fg=PALETTE["light"],
            insertbackground=PALETTE["white"],
            relief="flat",
            bd=0,
            wrap="word",
            font=("Consolas", 12),
            padx=14,
            pady=14,
            height=17,
            highlightthickness=1,
            highlightbackground="#272c42",
        )
        self.console.grid(row=1, column=0, sticky="nsew")
        self.console.tag_configure(
            "assistant_label",
            foreground=PALETTE["secondary"],
            font=("Segoe UI Semibold", 12),
            lmargin1=18,
            lmargin2=18,
            justify="left",
            background=PALETTE["console"],
        )
        self.console.tag_configure(
            "assistant_body",
            foreground=PALETTE["light"],
            font=("Consolas", 12),
            lmargin1=22,
            lmargin2=22,
            spacing1=6,
            spacing3=18,
            justify="left",
            background=PALETTE["console"],
        )
        self.console.tag_configure(
            "user_body",
            foreground=PALETTE["white"],
            font=("Consolas", 12),
            lmargin1=260,
            lmargin2=260,
            rmargin=22,
            spacing1=6,
            spacing3=18,
            justify="right",
            background=PALETTE["console_alt"],
        )
        self.console.configure(state="disabled")

        self.confirm_bar = tk.Frame(main, bg=PALETTE["surface"], padx=20, pady=0)
        self.confirm_message = tk.Label(
            self.confirm_bar,
            text="",
            font=("Segoe UI", 10),
            fg=PALETTE["gray_dark"],
            bg=PALETTE["surface"],
        )
        self.confirm_message.pack(side="left")
        tk.Button(
            self.confirm_bar,
            text="Yes",
            command=lambda: self._dispatch_command("yes", show_in_input=False),
            bg=PALETTE["primary"],
            fg=PALETTE["white"],
            activebackground=PALETTE["primary"],
            activeforeground=PALETTE["white"],
            relief="flat",
            bd=0,
            padx=16,
            pady=6,
            font=("Segoe UI Semibold", 10),
            cursor="hand2",
        ).pack(side="right")
        tk.Button(
            self.confirm_bar,
            text="Cancel",
            command=lambda: self._dispatch_command("cancel", show_in_input=False),
            bg=PALETTE["dark"],
            fg=PALETTE["white"],
            activebackground=PALETTE["dark"],
            activeforeground=PALETTE["white"],
            relief="flat",
            bd=0,
            padx=16,
            pady=6,
            font=("Segoe UI Semibold", 10),
            cursor="hand2",
        ).pack(side="right", padx=(0, 8))

        self.bottom = tk.Frame(main, bg=PALETTE["surface"], padx=16, pady=14)
        self.bottom.pack(fill="x", side="bottom")
        self.bottom.grid_columnconfigure(0, weight=1)

        self.voice_footer = tk.Frame(main, bg=PALETTE["surface"], padx=18, pady=12)
        self.voice_footer_label = tk.Label(
            self.voice_footer,
            textvariable=self.transcript_var,
            font=("Segoe UI", 10),
            fg=PALETTE["gray_dark"],
            bg="#f8f8ff",
            anchor="w",
            justify="left",
            padx=14,
            pady=10,
        )
        self.voice_footer_label.pack(fill="x")

        entry_wrap = tk.Frame(
            self.bottom,
            bg=PALETTE["surface"],
            bd=0,
            highlightthickness=1,
            highlightbackground="#dddff3",
        )
        entry_wrap.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        entry_wrap.grid_columnconfigure(0, weight=1)

        self.entry = tk.Entry(
            entry_wrap,
            textvariable=self.input_var,
            font=("Segoe UI", 12),
            bg=PALETTE["surface"],
            fg=PALETTE["dark"],
            relief="flat",
            bd=0,
            insertbackground=PALETTE["dark"],
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=14, pady=12)
        self.entry.bind("<Return>", lambda _event: self._submit_command())
        self.entry.bind("<KeyRelease>", self._handle_entry_key_release)
        self.entry.focus_set()

        tk.Button(
            self.bottom,
            text="Run",
            command=self._submit_command,
            bg=PALETTE["primary"],
            fg=PALETTE["white"],
            activebackground=PALETTE["primary"],
            activeforeground=PALETTE["white"],
            relief="flat",
            bd=0,
            padx=26,
            pady=12,
            font=("Segoe UI Semibold", 12),
            cursor="hand2",
        ).grid(row=0, column=1, sticky="e")

    def _build_status_panel(self, parent):
        shell = tk.Frame(
            parent,
            bg=PALETTE["shell"],
            bd=0,
            highlightthickness=1,
            highlightbackground=PALETTE["soft_border"],
        )
        shell.pack(anchor="w", fill="x")

        panel = tk.Frame(shell, bg=PALETTE["surface"], padx=14, pady=14)
        panel.pack(fill="x", padx=2, pady=2)

        tk.Frame(panel, bg="#c7bdf7", height=8, width=360).pack(fill="x", side="top", pady=(0, 16))
        header = tk.Frame(panel, bg=PALETTE["surface"])
        header.pack(fill="x")
        tk.Label(
            header,
            text="Navigation",
            font=("Segoe UI", 9),
            fg=PALETTE["gray"],
            bg=PALETTE["surface"],
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Overview",
            font=("Segoe UI Semibold", 12),
            fg=PALETTE["dark"],
            bg=PALETTE["surface"],
        ).pack(anchor="w", pady=(2, 0))

        nav_wrap = tk.Frame(panel, bg=PALETTE["surface"])
        nav_wrap.pack(fill="x", pady=(14, 0))
        nav_items = [
            ("overview", "Overview"),
            ("today", "Today"),
            ("events", "Events"),
            ("notes", "Notes"),
            ("memory", "Memory"),
        ]
        for key, label in nav_items:
            button = tk.Button(
                nav_wrap,
                text=label,
                command=lambda value=key: self._set_sidebar_section(value),
                relief="flat",
                bd=0,
                padx=10,
                pady=7,
                font=("Segoe UI Semibold", 9),
                cursor="hand2",
            )
            button.pack(side="left", padx=(0, 6))
            self.sidebar_section_buttons[key] = button

        self.sidebar_content_frame = tk.Frame(panel, bg=PALETTE["surface"])
        self.sidebar_content_frame.pack(fill="x", pady=(14, 0))
        self._refresh_sidebar_panel()

    def _set_sidebar_section(self, section):
        self.sidebar_section = section
        self._refresh_sidebar_panel()

    def _refresh_sidebar_panel(self):
        if not self.sidebar_content_frame:
            return

        for key, button in self.sidebar_section_buttons.items():
            if key == self.sidebar_section:
                button.configure(
                    bg=PALETTE["primary"],
                    fg=PALETTE["white"],
                    activebackground=PALETTE["primary"],
                    activeforeground=PALETTE["white"],
                )
            else:
                button.configure(
                    bg="#f1f2fc",
                    fg=PALETTE["gray_dark"],
                    activebackground="#f1f2fc",
                    activeforeground=PALETTE["gray_dark"],
                )

        for child in self.sidebar_content_frame.winfo_children():
            child.destroy()

        section = self.sidebar_section
        if section == "overview":
            self._build_overview_section(self.sidebar_content_frame)
        elif section == "today":
            self._build_side_section(self.sidebar_content_frame, "Today", self.daily_summary_var, PALETTE["primary"], first=True)
        elif section == "events":
            self._build_side_section(self.sidebar_content_frame, "Next Event", self.next_event_var, PALETTE["secondary"], first=True)
            self._build_side_section(self.sidebar_content_frame, "Calendar Titles", self.calendar_titles_var, PALETTE["blue"])
        elif section == "notes":
            self._build_side_section(self.sidebar_content_frame, "Latest Note", self.latest_note_var, PALETTE["cyan"], first=True)
        elif section == "memory":
            self._build_side_section(self.sidebar_content_frame, "Memory", self.memory_snapshot_var, PALETTE["orange"], first=True)

    def _build_overview_section(self, parent):
        rows = [
            ("Weather", self.weather_var, PALETTE["cyan"]),
            ("Health", self.health_var, PALETTE["green"]),
        ]

        for title, variable, accent in rows:
            row = tk.Frame(parent, bg=PALETTE["surface"])
            row.pack(fill="x", anchor="w", pady=(0 if title == "Weather" else 12, 0))
            tk.Label(
                row,
                text=title,
                font=("Segoe UI Semibold", 10),
                fg=accent,
                bg=PALETTE["surface"],
                width=8,
                anchor="w",
            ).pack(side="left")
            tk.Label(
                row,
                textvariable=variable,
                font=("Segoe UI", 10),
                fg=PALETTE["dark"],
                bg=PALETTE["surface"],
                wraplength=190,
                justify="left",
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

        self._build_side_section(parent, "Today", self.daily_summary_var, PALETTE["primary"])

    def _build_side_section(self, parent, title, variable, accent, first=False):
        if not first:
            tk.Frame(parent, bg="#edf0fb", height=1).pack(fill="x", pady=(11, 0))
        tk.Label(
            parent,
            text=title,
            font=("Segoe UI Semibold", 10),
            fg=accent,
            bg=PALETTE["surface"],
        ).pack(anchor="w", pady=(10, 0))
        tk.Label(
            parent,
            textvariable=variable,
            font=("Segoe UI", 9),
            fg=PALETTE["gray_dark"],
            bg=PALETTE["surface"],
            wraplength=214,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

    def _draw_logo(self, canvas):
        canvas.create_polygon(20, 18, 42, 30, 42, 56, 18, 34, fill="#e7b55a", outline="")
        canvas.create_polygon(98, 18, 76, 30, 76, 56, 100, 34, fill="#e7b55a", outline="")
        canvas.create_oval(28, 28, 90, 72, fill="#e7b55a", outline="")
        canvas.create_polygon(28, 58, 18, 92, 36, 106, 48, 70, fill=PALETTE["light"], outline="")
        canvas.create_polygon(90, 58, 100, 92, 82, 106, 70, 70, fill=PALETTE["light"], outline="")
        canvas.create_polygon(42, 74, 59, 112, 76, 74, 72, 98, 59, 110, 46, 98, fill="#d7d7db", outline="")
        canvas.create_polygon(47, 48, 59, 42, 71, 48, 68, 61, 59, 66, 50, 61, fill="#f3e7c8", outline="")
        canvas.create_oval(41, 47, 54, 60, fill="#b78b3e", outline="")
        canvas.create_oval(68, 49, 74, 55, fill=PALETTE["dark"], outline="")
        canvas.create_oval(56, 61, 63, 68, fill=PALETTE["dark"], outline="")
        canvas.create_line(59, 68, 59, 76, fill=PALETTE["light"], width=2)

    def _update_clock(self):
        now = datetime.datetime.now()
        self.time_var.set(now.strftime("%I:%M:%S %p"))
        self.date_var.set(now.strftime("%A, %d %B %Y"))
        self.root.after(1000, self._update_clock)

    def _refresh_cards(self):
        try:
            data = get_task_data()
            pending = [task for task in data.get("tasks", []) if not task.get("completed")]
            reminders = data.get("reminders", [])
            if pending or reminders:
                self.daily_summary_var.set("Assistant is ready for your next command.")
            else:
                self.daily_summary_var.set("Nothing pending right now.")
        except Exception:
            self.daily_summary_var.set("Status unavailable right now.")

        try:
            weather = get_weather_report("weather")
            self.weather_var.set(self._compact_weather(weather))
        except Exception:
            self.weather_var.set("Unavailable")

        try:
            health = get_system_status()
            self.health_var.set(self._compact_health(health))
        except Exception:
            self.health_var.set("Unavailable")

        try:
            events = []
            today = datetime.date.today()
            for event in get_event_data().get("events", []):
                try:
                    event_date = datetime.date.fromisoformat(event.get("date"))
                except Exception:
                    continue
                if event_date >= today:
                    events.append(event)
            events.sort(key=lambda item: (item.get("date") or "", item.get("time") or "23:59"))
            if events:
                event = events[0]
                title = event.get("title", "Untitled event")
                date_text = event.get("date", "")
                time_text = event.get("time") or ""
                line = title
                if date_text:
                    line += f" on {date_text}"
                if time_text:
                    line += f" at {time_text}"
                self.next_event_var.set(line)
            else:
                self.next_event_var.set("No upcoming events.")
        except Exception:
            self.next_event_var.set("Event summary unavailable.")

        try:
            calendar_titles = upcoming_google_calendar_title_lines(limit=3)
            if calendar_titles:
                self.calendar_titles_var.set(" | ".join(self._compact_text(item, 22) for item in calendar_titles))
            else:
                self.calendar_titles_var.set("No Google Calendar titles.")
        except Exception:
            self.calendar_titles_var.set("Calendar titles unavailable.")

        try:
            note_text = latest_note()
            note_text = note_text.replace("Your latest note is:", "").strip()
            self.latest_note_var.set(self._compact_text(note_text, 70))
        except Exception:
            self.latest_note_var.set("No saved notes.")

        try:
            language = get_memory("personal.assistant.preferred_response_language") or "default"
            tone = get_memory("personal.assistant.preferred_response_tone") or "friendly"
            self.memory_snapshot_var.set(f"Language: {language} | Tone: {tone}")
        except Exception:
            self.memory_snapshot_var.set("No saved preferences.")

        self.root.after(120000, self._refresh_cards)

    def _compact_text(self, text, limit):
        if not text:
            return "Unavailable"
        text = " ".join(str(text).split())
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    def _compact_health(self, text):
        if not text:
            return "Unavailable"
        cpu_match = __import__("re").search(r"CPU usage is currently ([0-9.]+)", text)
        ram_match = __import__("re").search(r"RAM usage is ([0-9.]+)", text)
        battery_match = __import__("re").search(r"Battery is at ([0-9.]+)%", text)
        parts = []
        if cpu_match:
            parts.append(f"CPU {cpu_match.group(1)}%")
        if ram_match:
            parts.append(f"RAM {ram_match.group(1)}%")
        if battery_match:
            parts.append(f"Battery {battery_match.group(1)}%")
        return " | ".join(parts) if parts else self._compact_text(text, 50)

    def _compact_weather(self, text):
        if not text:
            return "Unavailable"
        normalized = self._compact_text(text, 120)
        temperature_match = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:°|deg(?:ree)?s?)?\s*C", normalized, re.IGNORECASE)
        if temperature_match:
            return f"{temperature_match.group(1)} C"
        fallback_match = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:°|deg)", normalized, re.IGNORECASE)
        if fallback_match:
            return f"{fallback_match.group(1)} C"
        return self._compact_text(normalized, 18)

    def _load_startup_messages(self):
        return

    def _apply_response_mode(self):
        if self.mode_is_voice:
            voice_speak_module.set_response_mode("voice")
            self.activity_var.set("Listening")
            self.voice_orb_state = "listening"
            if self.bottom:
                self.bottom.pack_forget()
            if self.voice_footer and not self.voice_footer.winfo_manager():
                self.voice_footer.pack(fill="x", side="bottom")
        else:
            voice_speak_module.set_response_mode("text")
            self.activity_var.set("Ready")
            self.voice_orb_state = "idle"
            self.transcript_var.set("")
            if self.bottom and not self.bottom.winfo_manager():
                self.bottom.pack(fill="x", side="bottom")
            if self.voice_footer and self.voice_footer.winfo_manager():
                self.voice_footer.pack_forget()
            if self.entry:
                self.entry.focus_set()
        self._refresh_mode_buttons()
        self._draw_voice_orb()

    def _refresh_mode_buttons(self):
        if not self.text_mode_button or not self.voice_mode_button:
            return
        if self.mode_is_voice:
            self.text_mode_button.configure(
                bg="#20242f",
                fg=PALETTE["gray"],
                activebackground="#20242f",
                activeforeground=PALETTE["gray"],
            )
            self.voice_mode_button.configure(
                bg=PALETTE["orange"],
                fg=PALETTE["dark"],
                activebackground=PALETTE["orange"],
                activeforeground=PALETTE["dark"],
            )
        else:
            self.text_mode_button.configure(
                bg=PALETTE["primary"],
                fg=PALETTE["white"],
                activebackground=PALETTE["primary"],
                activeforeground=PALETTE["white"],
            )
            self.voice_mode_button.configure(
                bg="#20242f",
                fg=PALETTE["gray"],
                activebackground="#20242f",
                activeforeground=PALETTE["gray"],
            )

    def _set_text_mode(self):
        if self.mode_is_voice:
            self.voice_stop_requested = True
            self.mode_is_voice = False
            self._apply_response_mode()

    def _set_voice_mode(self):
        if not self.mode_is_voice:
            self.mode_is_voice = True
            self.voice_stop_requested = False
            self.transcript_var.set("Listening... Speak now.")
            self._apply_response_mode()
            self.voice_thread = threading.Thread(target=self._voice_loop, daemon=True)
            self.voice_thread.start()

    def _toggle_mode(self):
        if self.mode_is_voice:
            self._set_text_mode()
        else:
            self._set_voice_mode()

    def _toggle_voice(self):
        self._toggle_mode()

    def _voice_loop(self):
        while not self.voice_stop_requested:
            if self.command_running:
                time.sleep(0.2)
                continue

            self.root.after(0, lambda: self._set_voice_orb_state("listening", "Listening"))
            spoken = listen(for_wake_word=False)
            if self.voice_stop_requested:
                break
            if not spoken:
                continue

            self.root.after(0, lambda value=spoken: self.transcript_var.set(f"Heard: {value}"))

            self.root.after(0, lambda value=spoken: self._dispatch_command(value, show_in_input=False))
        self.mode_is_voice = False
        self.root.after(0, self._apply_response_mode)

    def _close_window(self):
        self.voice_stop_requested = True
        self.root.destroy()

    @contextlib.contextmanager
    def _patched_speaker(self):
        original_command_router_speak = command_router_module.speak
        original_voice_speak = self._real_voice_speak

        def ui_speak(text, *args, **kwargs):
            cleaned = self._clean_console_text(str(text))
            if not cleaned:
                return
            self.root.after(0, lambda value=cleaned: self._append_message("Grandpa", value, "assistant"))
            if self.mode_is_voice:
                self.root.after(0, lambda: self._set_voice_orb_state("speaking", "Speaking"))
                original_voice_speak(cleaned, already_printed=True)
                self.root.after(0, lambda: self._set_voice_orb_state("listening", "Listening"))

        command_router_module.speak = ui_speak
        voice_speak_module.speak = ui_speak
        try:
            yield
        finally:
            command_router_module.speak = original_command_router_speak
            voice_speak_module.speak = original_voice_speak

    def _submit_command(self):
        self._run_autocorrect()
        command = self.input_var.get().strip()
        if not command:
            return

        self.input_var.set("")
        self._dispatch_command(command, show_in_input=True)

    def _dispatch_command(self, command, show_in_input):
        cleaned = self._clean_console_text(command)
        if not cleaned:
            return
        self._append_message("You", cleaned, "you")
        self._hide_confirmation_bar()
        if show_in_input:
            self.input_var.set("")
        if self.mode_is_voice:
            self.transcript_var.set(f"Heard: {cleaned}")
        short_command = cleaned if len(cleaned) <= 36 else cleaned[:33].rstrip() + "..."
        self._set_voice_orb_state("thinking", f"Running: {short_command}")
        threading.Thread(target=self._execute_command, args=(cleaned,), daemon=True).start()

    def _execute_command(self, command):
        self.command_running = True
        spoken_messages = []
        buffer = io.StringIO()
        output = ""
        try:
            with self._patched_speaker():
                original_ui_append = self._append_message
                original_voice_speak = self._real_voice_speak

                def capture_speak(text, *args, **kwargs):
                    cleaned = self._clean_console_text(str(text))
                    if cleaned:
                        spoken_messages.append(cleaned)
                        self.root.after(0, lambda value=cleaned: original_ui_append("Grandpa", value, "assistant"))
                        if self.mode_is_voice:
                            self.root.after(0, lambda: self._set_voice_orb_state("speaking", "Speaking"))
                            original_voice_speak(cleaned, already_printed=True)
                            self.root.after(0, lambda: self._set_voice_orb_state("listening", "Listening"))

                command_router_module.speak = capture_speak
                voice_speak_module.speak = capture_speak
                with contextlib.redirect_stdout(buffer):
                    runner_error = {"value": None}

                    def run_router_command():
                        try:
                            command_router_module.process_command(
                                command.lower(),
                                self.installed_apps,
                                input_mode="text",
                            )
                        except Exception as error:
                            runner_error["value"] = error

                    runner = threading.Thread(target=run_router_command, daemon=True)
                    runner.start()
                    runner.join(self.COMMAND_TIMEOUT_SECONDS)

                    if runner.is_alive():
                        output = (
                            "Command is taking too long. "
                            "Please click Reload once and try again."
                        )
                        self.root.after(0, lambda: self._set_voice_orb_state("error", "Timeout"))
                    elif runner_error["value"] is not None:
                        output = "I hit a small interface issue while handling that command."
                        self.root.after(0, lambda: self._set_voice_orb_state("error", "Error"))
                    else:
                        output = self._sanitize_output(buffer.getvalue(), spoken_messages)
        except Exception:
            output = "I hit a small interface issue while handling that command."
            self.root.after(0, lambda: self._set_voice_orb_state("error", "Error"))
        finally:
            self.root.after(0, lambda value=output: self._finish_command(value))

    def _finish_command(self, output):
        if output:
            self._append_message("Grandpa", output, "assistant")
        self._refresh_cards()
        self.command_running = False
        if self.mode_is_voice:
            self._set_voice_orb_state("listening", "Listening")
            if not self.transcript_var.get():
                self.transcript_var.set("Listening... Speak now.")
        else:
            self._set_voice_orb_state("idle", "Ready")

    def _clean_console_text(self, text):
        cleaned = re.sub(r"\x1b\[[0-9;]*m", "", text or "")
        cleaned = cleaned.replace("\r", "")
        cleaned = "\n".join(line.strip() for line in cleaned.splitlines() if line.strip())
        return cleaned.strip()

    def _sanitize_output(self, raw_output, spoken_messages):
        cleaned = self._clean_console_text(raw_output)
        if not cleaned:
            return ""

        filtered_lines = []
        for line in cleaned.splitlines():
            normalized = line.strip()
            if normalized.startswith("Grandpa:") or normalized.startswith("You:"):
                continue
            if any(normalized == message or normalized in message or message in normalized for message in spoken_messages):
                continue
            filtered_lines.append(normalized)
        return "\n".join(filtered_lines).strip()

    def _append_message(self, speaker, text, tag):
        cleaned = self._clean_console_text(text)
        if not cleaned:
            return

        self.console.configure(state="normal")
        if tag == "assistant":
            self.console.insert("end", "Grandpa : ", ("assistant_label",))
            self.console.insert("end", f"{cleaned}\n\n", ("assistant_body",))
            if self._looks_like_confirmation(cleaned):
                self._show_confirmation_bar(cleaned)
            else:
                self._hide_confirmation_bar()
        else:
            self.console.insert("end", f"{cleaned}\n\n", ("user_body",))
        self.console.configure(state="disabled")
        self.console.see("end")

    def _reload_conversation(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")
        self.input_var.set("")
        self.transcript_var.set("")
        self._hide_confirmation_bar()
        if self.mode_is_voice:
            self._set_voice_orb_state("listening", "Listening")
        else:
            self._set_voice_orb_state("idle", "Ready")

    def _handle_entry_key_release(self, _event=None):
        if self._autocorrect_updating:
            return
        if not get_setting("ui.autocorrect_enabled", True):
            return
        if self._autocorrect_job is not None:
            try:
                self.root.after_cancel(self._autocorrect_job)
            except Exception:
                pass
        self._autocorrect_job = self.root.after(120, self._run_autocorrect)

    def _run_autocorrect(self):
        self._autocorrect_job = None
        if self._autocorrect_updating:
            return

        original_text = self.input_var.get()
        corrected_text = self._autocorrect_input_text(original_text)
        if corrected_text == original_text:
            return

        cursor_index = self.entry.index(tk.INSERT) if self.entry else len(corrected_text)
        length_delta = len(corrected_text) - len(original_text)

        self._autocorrect_updating = True
        try:
            self.input_var.set(corrected_text)
            if self.entry:
                self.entry.icursor(max(0, min(len(corrected_text), cursor_index + length_delta)))
        finally:
            self._autocorrect_updating = False

    def _autocorrect_input_text(self, text):
        if not text:
            return text

        corrected = re.sub(
            r"\b([A-Za-z']+)\b",
            lambda match: self._correct_word(match.group(1)),
            text,
        )
        corrected = re.sub(r"\bi\b", "I", corrected)
        corrected = re.sub(r"\s{2,}", " ", corrected)
        corrected = self._normalize_punctuation(corrected)

        stripped = corrected.lstrip()
        if stripped:
            first_index = corrected.find(stripped[0])
            corrected = corrected[:first_index] + stripped[0].upper() + stripped[1:]

        corrected = re.sub(r"([.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), corrected)
        return corrected

    def _correct_word(self, word):
        replacement = self.AUTO_CORRECT_MAP.get(word.lower())
        if not replacement:
            return word
        if word.isupper():
            return replacement.upper()
        if word[:1].isupper():
            return replacement[:1].upper() + replacement[1:]
        return replacement

    def _normalize_punctuation(self, text):
        if not text:
            return text

        normalized = text
        normalized = re.sub(r"\s+([,.;:!?])", r"\1", normalized)
        normalized = re.sub(r"([,.;:!?])([A-Za-z])", r"\1 \2", normalized)
        normalized = re.sub(r"([,.;:!?])\s{2,}", r"\1 ", normalized)
        normalized = re.sub(r",{2,}", ",", normalized)
        normalized = re.sub(r";{2,}", ";", normalized)
        normalized = re.sub(r":{2,}", ":", normalized)
        normalized = re.sub(r"!{2,}", "!", normalized)
        normalized = re.sub(r"\?{2,}", "?", normalized)
        normalized = re.sub(r"\.{4,}", "...", normalized)
        normalized = re.sub(r"(?<!\.)\.{2}(?!\.)", ".", normalized)
        return normalized

    def _looks_like_confirmation(self, text):
        normalized = (text or "").strip().lower()
        return (
            normalized.startswith("should i ")
            or normalized.startswith("do you want ")
            or normalized.startswith("are you sure ")
        )

    def _show_confirmation_bar(self, message):
        if not self.confirm_bar:
            return
        self.confirm_message.configure(text=message)
        if not self.confirm_bar.winfo_manager():
            self.confirm_bar.pack(fill="x", side="bottom", before=self.bottom, pady=(0, 2))

    def _hide_confirmation_bar(self):
        if self.confirm_bar and self.confirm_bar.winfo_manager():
            self.confirm_bar.pack_forget()

    def _set_voice_orb_state(self, state, activity_text=None):
        self.voice_orb_state = state
        if activity_text is not None:
            self.activity_var.set(activity_text)
        self._draw_voice_orb()

    def _draw_voice_orb(self):
        if not self.voice_orb_canvas:
            return
        canvas = self.voice_orb_canvas
        canvas.delete("all")

        state = self.voice_orb_state
        if state == "listening":
            outer = "#c8fff3"
            inner = PALETTE["teal"]
        elif state == "thinking":
            outer = "#efe2ff"
            inner = PALETTE["primary"]
        elif state == "speaking":
            outer = "#fff3d2"
            inner = PALETTE["orange"]
        elif state == "error":
            outer = "#ffd8de"
            inner = PALETTE["danger"]
        else:
            outer = "#eef0fb"
            inner = "#a8aec9"

        phase = self.voice_orb_phase if state in {"listening", "thinking", "speaking"} else 0
        expand = 1 if phase % 2 else 0
        canvas.create_oval(1 - expand, 1 - expand, 15 + expand, 15 + expand, fill=outer, outline="")
        canvas.create_oval(4, 4, 12, 12, fill=inner, outline="")

    def _animate_voice_orb(self):
        self.voice_orb_phase = (self.voice_orb_phase + 1) % 8
        if self.voice_orb_state in {"listening", "thinking", "speaking"}:
            self._draw_voice_orb()
        self.root.after(450, self._animate_voice_orb)

    def run(self):
        self.root.mainloop()


def launch_odin_ui(installed_apps, startup_messages=None):
    ui = OdinUI(installed_apps, startup_messages=startup_messages)
    ui.run()
