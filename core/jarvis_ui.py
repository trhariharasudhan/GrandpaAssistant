import datetime
import threading
import tkinter as tk
from contextlib import contextmanager
from tkinter import scrolledtext

import core.command_router as command_router
import modules.system_module as system_module
import voice.speak as voice_speak_module
from brain.database import get_recent_commands
from modules.dashboard_module import build_dashboard_report, build_today_agenda
from modules.event_module import get_event_data
from modules.health_module import get_system_status
from modules.task_module import get_task_data
from modules.weather_module import get_weather_report


class JarvisUI:
    def __init__(self, installed_apps):
        self.installed_apps = installed_apps
        self.root = tk.Tk()
        self.root.title("Grandpa Assistant Control Center")
        self.root.geometry("1360x860")
        self.root.minsize(1120, 720)
        self.root.configure(bg="#08141a")

        self._build_styles()
        self._build_layout()
        self._refresh_dashboard()
        self._tick_clock()

    def _build_styles(self):
        self.colors = {
            "bg": "#08141a",
            "panel": "#10232c",
            "panel_alt": "#132d38",
            "card": "#173947",
            "accent": "#f3b74f",
            "accent_alt": "#67d5c2",
            "text": "#edf6f2",
            "muted": "#9bb8bb",
            "danger": "#ff7b72",
            "success": "#77dd77",
            "border": "#245262",
        }

    def _panel(self, parent, **kwargs):
        defaults = {
            "bg": self.colors["panel"],
            "bd": 0,
            "highlightthickness": 1,
            "highlightbackground": self.colors["border"],
            "highlightcolor": self.colors["border"],
        }
        defaults.update(kwargs)
        return tk.Frame(parent, **defaults)

    def _label(self, parent, text="", size=12, bold=False, color=None, bg=None, **kwargs):
        return tk.Label(
            parent,
            text=text,
            fg=color or self.colors["text"],
            bg=bg or parent.cget("bg"),
            font=("Segoe UI", size, "bold" if bold else "normal"),
            **kwargs,
        )

    def _build_layout(self):
        root = self.root

        header = tk.Frame(root, bg=self.colors["bg"])
        header.pack(fill="x", padx=18, pady=(18, 12))

        title_wrap = tk.Frame(header, bg=self.colors["bg"])
        title_wrap.pack(side="left", fill="x", expand=True)
        self._label(title_wrap, "Grandpa Assistant", size=28, bold=True, color=self.colors["accent"]).pack(anchor="w")
        self._label(
            title_wrap,
            "Voice-first Jarvis control center for commands, context, and automation",
            size=11,
            color=self.colors["muted"],
        ).pack(anchor="w", pady=(4, 0))

        status_wrap = tk.Frame(header, bg=self.colors["bg"])
        status_wrap.pack(side="right", anchor="e")
        self.clock_label = self._label(status_wrap, "", size=18, bold=True, color=self.colors["accent_alt"])
        self.clock_label.pack(anchor="e")
        self.subtitle_label = self._label(status_wrap, "", size=10, color=self.colors["muted"])
        self.subtitle_label.pack(anchor="e", pady=(3, 0))

        body = tk.Frame(root, bg=self.colors["bg"])
        body.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left_col = tk.Frame(body, bg=self.colors["bg"], width=320)
        left_col.grid(row=0, column=0, sticky="nsw", padx=(0, 12))

        center_col = tk.Frame(body, bg=self.colors["bg"])
        center_col.grid(row=0, column=1, sticky="nsew", padx=(0, 12))
        center_col.grid_rowconfigure(1, weight=1)
        center_col.grid_columnconfigure(0, weight=1)

        right_col = tk.Frame(body, bg=self.colors["bg"], width=280)
        right_col.grid(row=0, column=2, sticky="nse")

        self._build_left_cards(left_col)
        self._build_center_console(center_col)
        self._build_right_actions(right_col)

    def _build_left_cards(self, parent):
        hero = self._panel(parent, bg=self.colors["panel_alt"])
        hero.pack(fill="x", pady=(0, 12))
        self._label(hero, "System Pulse", size=15, bold=True).pack(anchor="w", padx=14, pady=(14, 6))
        self.hero_status = self._label(hero, "", size=11, color=self.colors["muted"], justify="left", wraplength=280)
        self.hero_status.pack(anchor="w", padx=14, pady=(0, 14))

        agenda = self._panel(parent, bg=self.colors["card"])
        agenda.pack(fill="x", pady=(0, 12))
        self._label(agenda, "Today", size=14, bold=True).pack(anchor="w", padx=14, pady=(14, 6))
        self.agenda_label = self._label(agenda, "", size=10, color=self.colors["muted"], justify="left", wraplength=280)
        self.agenda_label.pack(anchor="w", padx=14, pady=(0, 14))

        memory = self._panel(parent)
        memory.pack(fill="x")
        self._label(memory, "Recent Commands", size=14, bold=True).pack(anchor="w", padx=14, pady=(14, 8))
        self.recent_commands_label = self._label(memory, "", size=10, color=self.colors["muted"], justify="left", wraplength=280)
        self.recent_commands_label.pack(anchor="w", padx=14, pady=(0, 14))

    def _build_center_console(self, parent):
        summary = self._panel(parent, bg=self.colors["panel_alt"])
        summary.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self._label(summary, "Mission Brief", size=15, bold=True).pack(anchor="w", padx=16, pady=(14, 6))
        self.dashboard_label = self._label(summary, "", size=10, color=self.colors["muted"], justify="left", wraplength=660)
        self.dashboard_label.pack(anchor="w", padx=16, pady=(0, 14))

        console_panel = self._panel(parent, bg="#0f1d24")
        console_panel.grid(row=1, column=0, sticky="nsew")
        console_panel.grid_rowconfigure(1, weight=1)
        console_panel.grid_columnconfigure(0, weight=1)

        self._label(console_panel, "Conversation Console", size=15, bold=True).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        self.console = scrolledtext.ScrolledText(
            console_panel,
            wrap="word",
            bg="#0b171d",
            fg=self.colors["text"],
            insertbackground=self.colors["accent"],
            selectbackground="#245262",
            relief="flat",
            font=("Consolas", 11),
            padx=12,
            pady=12,
        )
        self.console.grid(row=1, column=0, sticky="nsew", padx=14)
        self.console.configure(state="disabled")

        entry_wrap = tk.Frame(console_panel, bg=console_panel.cget("bg"))
        entry_wrap.grid(row=2, column=0, sticky="ew", padx=14, pady=14)
        entry_wrap.grid_columnconfigure(0, weight=1)

        self.command_entry = tk.Entry(
            entry_wrap,
            bg="#10232c",
            fg=self.colors["text"],
            insertbackground=self.colors["accent"],
            relief="flat",
            font=("Segoe UI", 12),
        )
        self.command_entry.grid(row=0, column=0, sticky="ew", ipady=10, padx=(0, 10))
        self.command_entry.bind("<Return>", lambda _event: self._submit_command())

        send_button = tk.Button(
            entry_wrap,
            text="Run Command",
            command=self._submit_command,
            bg=self.colors["accent"],
            fg="#1b1408",
            relief="flat",
            font=("Segoe UI", 11, "bold"),
            padx=16,
            cursor="hand2",
        )
        send_button.grid(row=0, column=1)

    def _build_right_actions(self, parent):
        quick = self._panel(parent, bg=self.colors["panel_alt"])
        quick.pack(fill="x", pady=(0, 12))
        self._label(quick, "Quick Actions", size=14, bold=True).pack(anchor="w", padx=14, pady=(14, 8))

        action_commands = [
            ("Today Agenda", "today agenda"),
            ("System Status", "system status"),
            ("Weather", "weather"),
            ("Show Settings", "show settings"),
            ("Run Morning Routine", "run morning routine"),
            ("Open Overlay", "open quick overlay"),
            ("Call Appa", "call appa"),
            ("Message Amma", "message to amma saying saptiya"),
        ]

        for label, command in action_commands:
            button = tk.Button(
                quick,
                text=label,
                command=lambda cmd=command: self._submit_command(cmd),
                bg="#0d7a72",
                fg="white",
                relief="flat",
                font=("Segoe UI", 10, "bold"),
                cursor="hand2",
                padx=10,
                pady=10,
                wraplength=220,
                justify="center",
            )
            button.pack(fill="x", padx=14, pady=(0, 10))

        status = self._panel(parent)
        status.pack(fill="both", expand=True)
        self._label(status, "Live Panels", size=14, bold=True).pack(anchor="w", padx=14, pady=(14, 8))

        self.weather_label = self._label(status, "", size=10, color=self.colors["muted"], justify="left", wraplength=220)
        self.weather_label.pack(anchor="w", padx=14, pady=(0, 12))

        self.health_label = self._label(status, "", size=10, color=self.colors["muted"], justify="left", wraplength=220)
        self.health_label.pack(anchor="w", padx=14, pady=(0, 12))

        self.events_label = self._label(status, "", size=10, color=self.colors["muted"], justify="left", wraplength=220)
        self.events_label.pack(anchor="w", padx=14, pady=(0, 14))

    def _append_console(self, speaker, text):
        self.console.configure(state="normal")
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.console.insert("end", f"[{timestamp}] {speaker}: {text}\n\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    @contextmanager
    def _patched_speakers(self):
        originals = {
            "command_router": command_router.speak,
            "system_module": system_module.speak,
            "voice_module": voice_speak_module.speak,
        }

        def ui_speak(text, *args, **kwargs):
            self.root.after(0, lambda: self._append_console("Grandpa", str(text)))

        command_router.speak = ui_speak
        system_module.speak = ui_speak
        voice_speak_module.speak = ui_speak
        try:
            yield
        finally:
            command_router.speak = originals["command_router"]
            system_module.speak = originals["system_module"]
            voice_speak_module.speak = originals["voice_module"]

    def _run_command_thread(self, command_text):
        with self._patched_speakers():
            try:
                command_router.process_command(command_text.lower().strip(), self.installed_apps, input_mode="text")
            except Exception as error:
                self.root.after(0, lambda: self._append_console("System", f"Command failed: {error}"))
        self.root.after(0, self._refresh_dashboard)

    def _submit_command(self, preset_command=None):
        command_text = preset_command or self.command_entry.get().strip()
        if not command_text:
            return

        if not preset_command:
            self.command_entry.delete(0, "end")

        self._append_console("You", command_text)
        threading.Thread(target=self._run_command_thread, args=(command_text,), daemon=True).start()

    def _tick_clock(self):
        now = datetime.datetime.now()
        self.clock_label.config(text=now.strftime("%I:%M %p"))
        self.subtitle_label.config(text=now.strftime("%A, %d %B %Y"))
        self.root.after(1000, self._tick_clock)

    def _refresh_dashboard(self):
        try:
            self.dashboard_label.config(text=build_dashboard_report())
        except Exception:
            self.dashboard_label.config(text="Dashboard summary is not available right now.")

        try:
            self.hero_status.config(text=get_system_status())
        except Exception:
            self.hero_status.config(text="System health summary is not available right now.")

        try:
            self.agenda_label.config(text=build_today_agenda())
        except Exception:
            self.agenda_label.config(text="Today agenda is not available right now.")

        try:
            recent = get_recent_commands(limit=6)
            if recent:
                recent_text = " | ".join(recent)
            else:
                recent_text = "No recent commands yet."
            self.recent_commands_label.config(text=recent_text)
        except Exception:
            self.recent_commands_label.config(text="Recent commands are not available right now.")

        try:
            self.weather_label.config(text=get_weather_report("weather"))
        except Exception:
            self.weather_label.config(text="Weather report is not available right now.")

        try:
            self.health_label.config(text=get_system_status())
        except Exception:
            self.health_label.config(text="Health panel is not available right now.")

        try:
            events = get_event_data().get("events", [])
            upcoming = sorted(
                [event for event in events if event.get("date")],
                key=lambda item: (item.get("date") or "9999-12-31", item.get("time") or "23:59"),
            )
            if upcoming:
                lines = []
                for event in upcoming[:3]:
                    line = event.get("title", "Untitled event")
                    if event.get("time"):
                        line += f" at {event.get('time')}"
                    lines.append(line)
                self.events_label.config(text="Upcoming: " + " | ".join(lines))
            else:
                self.events_label.config(text="No upcoming events right now.")
        except Exception:
            self.events_label.config(text="Event panel is not available right now.")

        try:
            task_data = get_task_data()
            pending_count = sum(1 for item in task_data.get("tasks", []) if not item.get("completed"))
            reminder_count = len(task_data.get("reminders", []))
            self.root.title(f"Grandpa Assistant Control Center  |  {pending_count} tasks  |  {reminder_count} reminders")
        except Exception:
            pass

        self.root.after(15000, self._refresh_dashboard)

    def run(self):
        self.command_entry.focus_set()
        self.root.mainloop()


def launch_jarvis_ui(installed_apps):
    ui = JarvisUI(installed_apps)
    ui.run()
