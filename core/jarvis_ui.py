import contextlib
import datetime
import io
import threading
import tkinter as tk
from tkinter import ttk

from brain.database import get_recent_commands
from core.command_router import process_command
from modules.health_module import get_system_status
from modules.task_module import get_task_data
from modules.weather_module import get_weather_report


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
}


class JarvisUI:
    def __init__(self, installed_apps):
        self.installed_apps = installed_apps
        self.root = tk.Tk()
        self.root.title("Grandpa Assistant")
        self.root.geometry("1180x760")
        self.root.minsize(1040, 680)
        self.root.configure(bg=PALETTE["light"])

        self.time_var = tk.StringVar()
        self.date_var = tk.StringVar()
        self.input_var = tk.StringVar()
        self.tasks_var = tk.StringVar(value="0 pending")
        self.reminders_var = tk.StringVar(value="0 reminders")
        self.weather_var = tk.StringVar(value="Weather unavailable")
        self.health_var = tk.StringVar(value="Health unavailable")

        self._configure_styles()
        self._build_layout()
        self._update_clock()
        self._refresh_cards()

    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Jarvis.TFrame",
            background=PALETTE["light"],
        )
        style.configure(
            "JarvisCard.TFrame",
            background=PALETTE["white"],
            borderwidth=0,
        )
        style.configure(
            "Jarvis.TEntry",
            fieldbackground=PALETTE["white"],
            foreground=PALETTE["dark"],
            borderwidth=0,
            padding=10,
        )

    def _build_layout(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        outer = tk.Frame(self.root, bg=PALETTE["light"], padx=28, pady=24)
        outer.grid(sticky="nsew")
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(2, weight=1)

        header = tk.Frame(outer, bg=PALETTE["light"])
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        logo_wrap = tk.Frame(header, bg=PALETTE["light"])
        logo_wrap.grid(row=0, column=0, sticky="w")

        logo = tk.Canvas(
            logo_wrap,
            width=92,
            height=92,
            bg=PALETTE["light"],
            highlightthickness=0,
            bd=0,
        )
        logo.pack(side="left")
        self._draw_logo(logo)

        title_wrap = tk.Frame(logo_wrap, bg=PALETTE["light"])
        title_wrap.pack(side="left", padx=(14, 0))
        tk.Label(
            title_wrap,
            text="Grandpa Assistant",
            font=("Segoe UI Semibold", 28),
            fg=PALETTE["dark"],
            bg=PALETTE["light"],
        ).pack(anchor="w")
        tk.Label(
            title_wrap,
            text="Simple voice-first control center",
            font=("Segoe UI", 12),
            fg=PALETTE["gray"],
            bg=PALETTE["light"],
        ).pack(anchor="w", pady=(2, 0))

        time_wrap = tk.Frame(header, bg=PALETTE["light"])
        time_wrap.grid(row=0, column=1, sticky="e")
        tk.Label(
            time_wrap,
            textvariable=self.time_var,
            font=("Segoe UI Semibold", 24),
            fg=PALETTE["primary"],
            bg=PALETTE["light"],
        ).pack(anchor="e")
        tk.Label(
            time_wrap,
            textvariable=self.date_var,
            font=("Segoe UI", 12),
            fg=PALETTE["gray"],
            bg=PALETTE["light"],
        ).pack(anchor="e")

        cards = tk.Frame(outer, bg=PALETTE["light"])
        cards.grid(row=1, column=0, sticky="ew", pady=(22, 20))
        for index in range(4):
            cards.grid_columnconfigure(index, weight=1)

        self._build_card(cards, 0, "Tasks", self.tasks_var, PALETTE["primary"])
        self._build_card(cards, 1, "Reminders", self.reminders_var, PALETTE["secondary"])
        self._build_card(cards, 2, "Weather", self.weather_var, PALETTE["cyan"])
        self._build_card(cards, 3, "Health", self.health_var, PALETTE["green"])

        main = tk.Frame(outer, bg=PALETTE["white"], bd=0, highlightthickness=0)
        main.grid(row=2, column=0, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        quick = tk.Frame(main, bg=PALETTE["white"], padx=22, pady=18)
        quick.grid(row=0, column=0, sticky="ew")
        tk.Label(
            quick,
            text="Quick Actions",
            font=("Segoe UI Semibold", 13),
            fg=PALETTE["dark"],
            bg=PALETTE["white"],
        ).pack(anchor="w")

        quick_buttons = tk.Frame(quick, bg=PALETTE["white"])
        quick_buttons.pack(anchor="w", pady=(12, 0), fill="x")

        actions = [
            ("Today Agenda", "today agenda", PALETTE["primary"]),
            ("System Status", "system status", PALETTE["dark"]),
            ("Weather", "weather", PALETTE["secondary"]),
            ("Call Appa", "call appa", PALETTE["success"]),
        ]
        for text, command, color in actions:
            tk.Button(
                quick_buttons,
                text=text,
                command=lambda value=command: self._run_quick_action(value),
                bg=color,
                fg=PALETTE["white"] if color != PALETTE["secondary"] else PALETTE["dark"],
                activebackground=color,
                activeforeground=PALETTE["white"] if color != PALETTE["secondary"] else PALETTE["dark"],
                relief="flat",
                bd=0,
                padx=16,
                pady=10,
                font=("Segoe UI Semibold", 11),
                cursor="hand2",
            ).pack(side="left", padx=(0, 10))

        console_wrap = tk.Frame(main, bg=PALETTE["white"], padx=22, pady=(0, 18))
        console_wrap.grid(row=1, column=0, sticky="nsew")
        console_wrap.grid_columnconfigure(0, weight=1)
        console_wrap.grid_rowconfigure(1, weight=1)

        tk.Label(
            console_wrap,
            text="Conversation",
            font=("Segoe UI Semibold", 13),
            fg=PALETTE["dark"],
            bg=PALETTE["white"],
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.console = tk.Text(
            console_wrap,
            bg=PALETTE["dark"],
            fg=PALETTE["light"],
            insertbackground=PALETTE["white"],
            relief="flat",
            bd=0,
            wrap="word",
            font=("Consolas", 12),
            padx=16,
            pady=16,
        )
        self.console.grid(row=1, column=0, sticky="nsew")
        self.console.tag_configure("you", foreground=PALETTE["secondary"], font=("Segoe UI Semibold", 11))
        self.console.tag_configure("assistant", foreground=PALETTE["cyan"], font=("Segoe UI Semibold", 11))
        self.console.tag_configure("body", foreground=PALETTE["light"], font=("Consolas", 12))
        self.console.insert("end", "Assistant ready.\n\n", ("assistant", "body"))
        self.console.configure(state="disabled")

        bottom = tk.Frame(main, bg=PALETTE["white"], padx=22, pady=(0, 22))
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.grid_columnconfigure(0, weight=1)

        entry_wrap = tk.Frame(bottom, bg=PALETTE["light"], bd=0, highlightthickness=0)
        entry_wrap.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        entry_wrap.grid_columnconfigure(0, weight=1)

        entry = tk.Entry(
            entry_wrap,
            textvariable=self.input_var,
            font=("Segoe UI", 12),
            bg=PALETTE["light"],
            fg=PALETTE["dark"],
            relief="flat",
            bd=0,
            insertbackground=PALETTE["dark"],
        )
        entry.grid(row=0, column=0, sticky="ew", padx=16, pady=14)
        entry.bind("<Return>", lambda _event: self._submit_command())
        entry.focus_set()

        tk.Button(
            bottom,
            text="Run",
            command=self._submit_command,
            bg=PALETTE["primary"],
            fg=PALETTE["white"],
            activebackground=PALETTE["primary"],
            activeforeground=PALETTE["white"],
            relief="flat",
            bd=0,
            padx=24,
            pady=14,
            font=("Segoe UI Semibold", 12),
            cursor="hand2",
        ).grid(row=0, column=1, sticky="e")

    def _build_card(self, parent, column, title, variable, accent):
        card = tk.Frame(parent, bg=PALETTE["white"], padx=18, pady=16)
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 10, 0))
        tk.Frame(card, bg=accent, height=4).pack(fill="x", side="top", pady=(0, 12))
        tk.Label(
            card,
            text=title,
            font=("Segoe UI Semibold", 11),
            fg=PALETTE["gray"],
            bg=PALETTE["white"],
        ).pack(anchor="w")
        tk.Label(
            card,
            textvariable=variable,
            font=("Segoe UI Semibold", 14),
            fg=PALETTE["dark"],
            bg=PALETTE["white"],
            wraplength=210,
            justify="left",
        ).pack(anchor="w", pady=(6, 0))

    def _draw_logo(self, canvas):
        canvas.create_polygon(18, 14, 32, 24, 32, 48, 12, 26, fill=PALETTE["secondary"], outline="")
        canvas.create_polygon(74, 14, 60, 24, 60, 48, 80, 26, fill=PALETTE["secondary"], outline="")
        canvas.create_oval(23, 28, 69, 66, fill=PALETTE["secondary"], outline="")
        canvas.create_polygon(24, 50, 14, 76, 30, 90, 38, 62, fill=PALETTE["light"], outline="")
        canvas.create_polygon(68, 50, 78, 76, 62, 90, 54, 62, fill=PALETTE["light"], outline="")
        canvas.create_polygon(30, 60, 46, 88, 62, 60, 60, 84, 46, 92, 32, 84, fill=PALETTE["gray"], outline="")
        canvas.create_oval(28, 42, 42, 55, fill=PALETTE["orange"], outline="")
        canvas.create_oval(52, 44, 57, 49, fill=PALETTE["dark"], outline="")
        canvas.create_oval(43, 52, 49, 58, fill=PALETTE["dark"], outline="")

    def _update_clock(self):
        now = datetime.datetime.now()
        self.time_var.set(now.strftime("%I:%M %p"))
        self.date_var.set(now.strftime("%A, %d %B %Y"))
        self.root.after(1000, self._update_clock)

    def _refresh_cards(self):
        try:
            data = get_task_data()
            pending = [task for task in data.get("tasks", []) if not task.get("completed")]
            reminders = data.get("reminders", [])
            self.tasks_var.set(f"{len(pending)} pending")
            self.reminders_var.set(f"{len(reminders)} reminders")
        except Exception:
            self.tasks_var.set("Unavailable")
            self.reminders_var.set("Unavailable")

        try:
            weather = get_weather_report("weather")
            self.weather_var.set(self._compact_text(weather, 50))
        except Exception:
            self.weather_var.set("Unavailable")

        try:
            health = get_system_status()
            self.health_var.set(self._compact_health(health))
        except Exception:
            self.health_var.set("Unavailable")

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

    def _run_quick_action(self, command):
        self.input_var.set(command)
        self._submit_command()

    def _submit_command(self):
        command = self.input_var.get().strip()
        if not command:
            return

        self.input_var.set("")
        self._append_message("You", command, "you")
        threading.Thread(target=self._execute_command, args=(command,), daemon=True).start()

    def _execute_command(self, command):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            try:
                process_command(command.lower(), self.installed_apps, input_mode="text")
            except Exception as error:
                output = f"Assistant error: {error}"
            else:
                output = buffer.getvalue().strip() or "Command completed."

        self.root.after(0, lambda: self._finish_command(output))

    def _finish_command(self, output):
        self._append_message("Grandpa", output, "assistant")
        self._refresh_cards()

    def _append_message(self, speaker, text, tag):
        self.console.configure(state="normal")
        self.console.insert("end", f"{speaker}: ", tag)
        self.console.insert("end", f"{text}\n\n", "body")
        self.console.configure(state="disabled")
        self.console.see("end")

    def run(self):
        self.root.mainloop()


def launch_jarvis_ui(installed_apps):
    ui = JarvisUI(installed_apps)
    ui.run()
