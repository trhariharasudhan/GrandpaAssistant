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
        header.pack(fill="x", padx=24, pady=(24, 10))

        title_wrap = tk.Frame(header, bg=self.colors["bg"])
        title_wrap.pack(side="left", fill="x", expand=True)
        self._label(title_wrap, "Grandpa Assistant", size=30, bold=True, color=self.colors["accent"]).pack(anchor="w")
        self._label(
            title_wrap,
            "Simple control center",
            size=12,
            color=self.colors["muted"],
        ).pack(anchor="w", pady=(4, 0))

        status_wrap = tk.Frame(header, bg=self.colors["bg"])
        status_wrap.pack(side="right", anchor="e")
        self.clock_label = self._label(status_wrap, "", size=18, bold=True, color=self.colors["accent_alt"])
        self.clock_label.pack(anchor="e")
        self.subtitle_label = self._label(status_wrap, "", size=10, color=self.colors["muted"])
        self.subtitle_label.pack(anchor="e", pady=(3, 0))

        status_panel = self._panel(root, bg=self.colors["panel_alt"])
        status_panel.pack(fill="x", padx=24, pady=(0, 10))
        self.status_values = {}

        for index, label in enumerate(["Tasks", "Reminders", "Weather", "Health"]):
            card = tk.Frame(status_panel, bg=status_panel.cget("bg"))
            card.grid(row=0, column=index, sticky="ew", padx=(12 if index == 0 else 8, 12 if index == 3 else 0), pady=12)
            status_panel.grid_columnconfigure(index, weight=1)
            self._label(card, label, size=10, bold=True, color=self.colors["muted"]).pack(anchor="w")
            value_label = self._label(card, "-", size=12, bold=True)
            value_label.pack(anchor="w", pady=(4, 0))
            self.status_values[label.lower()] = value_label

        quick_panel = self._panel(root)
        quick_panel.pack(fill="x", padx=24, pady=(0, 10))
        self._label(quick_panel, "Quick Actions", size=12, bold=True, color=self.colors["muted"]).pack(anchor="w", padx=14, pady=(10, 8))

        quick_wrap = tk.Frame(quick_panel, bg=quick_panel.cget("bg"))
        quick_wrap.pack(fill="x", padx=12, pady=(0, 12))

        action_commands = [
            ("Agenda", "today agenda"),
            ("Weather", "weather"),
            ("System", "system status"),
            ("Call Appa", "call appa"),
            ("Message Amma", "message to amma saying saptiya"),
            ("Settings", "show settings"),
        ]

        for index, (label, command) in enumerate(action_commands):
            button = tk.Button(
                quick_wrap,
                text=label,
                command=lambda cmd=command: self._submit_command(cmd),
                bg="#155e75",
                fg="white",
                relief="flat",
                font=("Segoe UI", 10, "bold"),
                cursor="hand2",
                padx=14,
                pady=8,
            )
            button.grid(row=0, column=index, padx=(0, 8), sticky="w")

        console_panel = self._panel(root, bg="#0f1d24")
        console_panel.pack(fill="both", expand=True, padx=24, pady=(0, 18))
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
        task_data = get_task_data()
        pending_count = sum(1 for item in task_data.get("tasks", []) if not item.get("completed"))
        reminder_count = len(task_data.get("reminders", []))

        self.status_values["tasks"].config(text=f"{pending_count} pending")
        self.status_values["reminders"].config(text=f"{reminder_count} active")

        try:
            weather = get_weather_report("weather")
            self.status_values["weather"].config(text=(weather.split(".")[0].strip() if weather else "Unavailable")[:34])
        except Exception:
            self.status_values["weather"].config(text="Unavailable")

        try:
            health_text = get_system_status()
            short_health = "Healthy" if health_text else "Unavailable"
            self.status_values["health"].config(text=short_health)
        except Exception:
            self.status_values["health"].config(text="Unavailable")

        self.root.title(f"Grandpa Assistant  |  {pending_count} tasks  |  {reminder_count} reminders")

        self.root.after(15000, self._refresh_dashboard)

    def run(self):
        self.command_entry.focus_set()
        self.root.mainloop()


def launch_jarvis_ui(installed_apps):
    ui = JarvisUI(installed_apps)
    ui.run()
