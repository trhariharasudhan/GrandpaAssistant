import contextlib
import datetime
import io
import re
import threading
import time
import tkinter as tk
from tkinter import ttk

import core.command_router as command_router_module
from modules.health_module import get_system_status
from modules.task_module import get_task_data
from modules.weather_module import get_weather_report
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
}


class JarvisUI:
    def __init__(self, installed_apps, startup_messages=None):
        self.installed_apps = installed_apps
        self.startup_messages = startup_messages or []
        self.root = tk.Tk()
        self.root.title("Grandpa Assistant")
        self.root.geometry("1180x760")
        self.root.minsize(1040, 680)
        self.root.configure(bg=PALETTE["light"])

        self.time_var = tk.StringVar()
        self.date_var = tk.StringVar()
        self.input_var = tk.StringVar()
        self.voice_state_var = tk.StringVar(value="Text Mode")
        self.tasks_var = tk.StringVar(value="0 pending")
        self.reminders_var = tk.StringVar(value="0 reminders")
        self.weather_var = tk.StringVar(value="Weather unavailable")
        self.health_var = tk.StringVar(value="Health unavailable")
        self.voice_thread = None
        self.voice_stop_requested = False
        self.command_running = False
        self._real_voice_speak = voice_speak_module.speak
        self.mode_is_voice = False
        self.mode_toggle_canvas = None
        self.bottom = None
        self.entry = None

        self._configure_styles()
        self._build_layout()
        self._update_clock()
        self._refresh_cards()
        self._load_startup_messages()
        self._apply_response_mode()
        self.root.protocol("WM_DELETE_WINDOW", self._close_window)

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
            width=118,
            height=118,
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
        voice_row = tk.Frame(title_wrap, bg=PALETTE["light"])
        voice_row.pack(anchor="w", pady=(8, 0))
        tk.Label(
            voice_row,
            textvariable=self.voice_state_var,
            font=("Segoe UI Semibold", 11),
            fg=PALETTE["success"],
            bg=PALETTE["light"],
        ).pack(side="left")
        self.mode_toggle_canvas = tk.Canvas(
            voice_row,
            width=72,
            height=34,
            bg=PALETTE["light"],
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.mode_toggle_canvas.pack(side="left", padx=(12, 0))
        self.mode_toggle_canvas.bind("<Button-1>", lambda _event: self._toggle_mode())
        self._draw_mode_toggle()

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
        cards.grid(row=1, column=0, sticky="ew", pady=(18, 16))
        for index in range(4):
            cards.grid_columnconfigure(index, weight=1)

        self._build_card(cards, 0, "Tasks", self.tasks_var, PALETTE["primary"])
        self._build_card(cards, 1, "Reminders", self.reminders_var, PALETTE["secondary"])
        self._build_card(cards, 2, "Weather", self.weather_var, PALETTE["cyan"])
        self._build_card(cards, 3, "Health", self.health_var, PALETTE["green"])

        main = tk.Frame(outer, bg=PALETTE["white"], bd=0, highlightthickness=0)
        main.grid(row=2, column=0, sticky="nsew")

        console_wrap = tk.Frame(main, bg=PALETTE["white"], padx=22, pady=0)
        console_wrap.pack(fill="both", expand=True)
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
            height=16,
        )
        self.console.grid(row=1, column=0, sticky="nsew")
        self.console.tag_configure(
            "assistant_label",
            foreground=PALETTE["secondary"],
            font=("Segoe UI Semibold", 12),
            lmargin1=12,
            lmargin2=12,
            justify="left",
        )
        self.console.tag_configure(
            "assistant_body",
            foreground=PALETTE["light"],
            font=("Consolas", 12),
            lmargin1=0,
            lmargin2=12,
            spacing3=12,
            justify="left",
        )
        self.console.tag_configure(
            "user_body",
            foreground=PALETTE["white"],
            font=("Consolas", 12),
            rmargin=12,
            spacing3=12,
            justify="right",
        )
        self.console.insert("end", "Grandpa : ", ("assistant_label",))
        self.console.insert("end", "Assistant ready.\n\n", ("assistant_body",))
        self.console.configure(state="disabled")

        self.bottom = tk.Frame(main, bg=PALETTE["white"], padx=22, pady=16)
        self.bottom.pack(fill="x", side="bottom")
        self.bottom.grid_columnconfigure(0, weight=1)

        entry_wrap = tk.Frame(self.bottom, bg=PALETTE["light"], bd=0, highlightthickness=0)
        entry_wrap.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        entry_wrap.grid_columnconfigure(0, weight=1)

        self.entry = tk.Entry(
            entry_wrap,
            textvariable=self.input_var,
            font=("Segoe UI", 12),
            bg=PALETTE["light"],
            fg=PALETTE["dark"],
            relief="flat",
            bd=0,
            insertbackground=PALETTE["dark"],
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=16, pady=14)
        self.entry.bind("<Return>", lambda _event: self._submit_command())
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
            font=("Segoe UI Semibold", 13),
            fg=PALETTE["dark"],
            bg=PALETTE["white"],
            wraplength=190,
            justify="left",
        ).pack(anchor="w", pady=(6, 0))

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

    def _load_startup_messages(self):
        for message in self.startup_messages:
            self._append_message("Grandpa", message, "assistant")

    def _apply_response_mode(self):
        if self.mode_is_voice:
            voice_speak_module.set_response_mode("voice")
            self.voice_state_var.set("Voice Mode")
            if self.bottom:
                self.bottom.pack_forget()
        else:
            voice_speak_module.set_response_mode("text")
            self.voice_state_var.set("Text Mode")
            if self.bottom and not self.bottom.winfo_manager():
                self.bottom.pack(fill="x", side="bottom")
            if self.entry:
                self.entry.focus_set()
        self._draw_mode_toggle()

    def _draw_mode_toggle(self):
        if not self.mode_toggle_canvas:
            return
        canvas = self.mode_toggle_canvas
        canvas.delete("all")
        bg = PALETTE["dark"] if self.mode_is_voice else "#20232d"
        glow = PALETTE["orange"] if self.mode_is_voice else PALETTE["gray_dark"]
        knob_x = 50 if self.mode_is_voice else 22
        canvas.create_oval(4, 4, 68, 30, fill=bg, outline="")
        canvas.create_oval(8, 8, 64, 26, fill=PALETTE["dark"], outline="")
        canvas.create_oval(knob_x - 12, 5, knob_x + 12, 29, fill="#1b1f29", outline=glow, width=2)
        canvas.create_oval(10, 12, 14, 16, fill=PALETTE["danger"], outline="")

    def _toggle_mode(self):
        if self.mode_is_voice:
            self.voice_stop_requested = True
            self.mode_is_voice = False
            self._apply_response_mode()
            self._append_message("Grandpa", "Switched to text mode.", "assistant")
            return

        self.mode_is_voice = True
        self.voice_stop_requested = False
        self._apply_response_mode()
        self._append_message("Grandpa", "Voice mode active.", "assistant")
        self.voice_thread = threading.Thread(target=self._voice_loop, daemon=True)
        self.voice_thread.start()

    def _toggle_voice(self):
        self._toggle_mode()

    def _voice_loop(self):
        while not self.voice_stop_requested:
            if self.command_running:
                time.sleep(0.2)
                continue

            spoken = listen(for_wake_word=False)
            if self.voice_stop_requested:
                break
            if not spoken:
                continue

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
                original_voice_speak(cleaned, already_printed=True)

        command_router_module.speak = ui_speak
        voice_speak_module.speak = ui_speak
        try:
            yield
        finally:
            command_router_module.speak = original_command_router_speak
            voice_speak_module.speak = original_voice_speak

    def _submit_command(self):
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
        if show_in_input:
            self.input_var.set("")
        threading.Thread(target=self._execute_command, args=(cleaned,), daemon=True).start()

    def _execute_command(self, command):
        self.command_running = True
        spoken_messages = []
        buffer = io.StringIO()
        with self._patched_speaker():
            original_ui_append = self._append_message
            original_voice_speak = self._real_voice_speak

            def capture_speak(text, *args, **kwargs):
                cleaned = self._clean_console_text(str(text))
                if cleaned:
                    spoken_messages.append(cleaned)
                    self.root.after(0, lambda value=cleaned: original_ui_append("Grandpa", value, "assistant"))
                    if self.mode_is_voice:
                        original_voice_speak(cleaned, already_printed=True)

            command_router_module.speak = capture_speak
            voice_speak_module.speak = capture_speak
            with contextlib.redirect_stdout(buffer):
                try:
                    command_router_module.process_command(command.lower(), self.installed_apps, input_mode="text")
                except Exception as error:
                    output = "I hit a small interface issue while handling that command."
                else:
                    output = self._sanitize_output(buffer.getvalue(), spoken_messages)

        self.root.after(0, lambda: self._finish_command(output))

    def _finish_command(self, output):
        if output:
            self._append_message("Grandpa", output, "assistant")
        self._refresh_cards()
        self.command_running = False

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
        else:
            self.console.insert("end", f"{cleaned}\n\n", ("user_body",))
        self.console.configure(state="disabled")
        self.console.see("end")

    def run(self):
        self.root.mainloop()


def launch_jarvis_ui(installed_apps, startup_messages=None):
    ui = JarvisUI(installed_apps, startup_messages=startup_messages)
    ui.run()
