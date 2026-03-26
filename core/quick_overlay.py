import threading
import tkinter as tk

try:
    import keyboard
except ImportError:
    keyboard = None


_overlay_root = None
_overlay_entry = None
_overlay_handler = None
_overlay_recent_frame = None
_overlay_suggestion_frame = None
_overlay_hotkey_handler = None
_overlay_hotkey_registered = None
_overlay_lock = threading.Lock()


def _destroy_overlay():
    global _overlay_root, _overlay_entry, _overlay_recent_frame, _overlay_suggestion_frame

    if _overlay_root is None:
        return False

    try:
        _overlay_root.destroy()
    except Exception:
        pass

    _overlay_root = None
    _overlay_entry = None
    _overlay_recent_frame = None
    _overlay_suggestion_frame = None
    return True


def _clear_frame(frame):
    if frame is None:
        return
    for child in frame.winfo_children():
        child.destroy()


def _make_chip(parent, text, command_text, on_submit, bg="#1f2937", fg="white"):
    button = tk.Button(
        parent,
        text=text,
        command=lambda: on_submit(command_text),
        bg=bg,
        fg=fg,
        activebackground="#374151",
        activeforeground="white",
        relief="flat",
        padx=8,
        pady=4,
        font=("Segoe UI", 9),
        cursor="hand2",
        wraplength=180,
        justify="left",
    )
    return button


def _refresh_overlay_lists(suggestions=None, recent_commands=None):
    if _overlay_recent_frame is None or _overlay_suggestion_frame is None or _overlay_handler is None:
        return

    _clear_frame(_overlay_suggestion_frame)
    _clear_frame(_overlay_recent_frame)

    suggestions = suggestions or []
    recent_commands = recent_commands or []

    for index, item in enumerate(suggestions):
        chip = _make_chip(
            _overlay_suggestion_frame,
            item,
            item,
            _overlay_handler,
            bg="#0f766e",
        )
        chip.grid(row=index // 3, column=index % 3, padx=4, pady=4, sticky="w")

    for index, item in enumerate(recent_commands):
        chip = _make_chip(
            _overlay_recent_frame,
            item,
            item,
            _overlay_handler,
            bg="#1f2937",
        )
        chip.grid(row=index // 2, column=index % 2, padx=4, pady=4, sticky="w")


def show_quick_overlay(on_submit, suggestions=None, recent_commands=None):
    global _overlay_root, _overlay_entry, _overlay_handler, _overlay_recent_frame, _overlay_suggestion_frame

    _overlay_handler = on_submit

    if _overlay_root is not None:
        try:
            _refresh_overlay_lists(suggestions=suggestions, recent_commands=recent_commands)
            _overlay_root.deiconify()
            _overlay_root.lift()
            _overlay_root.attributes("-topmost", True)
            if _overlay_entry is not None:
                _overlay_entry.focus_force()
                _overlay_entry.selection_range(0, "end")
            return True, "Quick command overlay opened."
        except Exception:
            _destroy_overlay()

    def worker():
        global _overlay_root, _overlay_entry, _overlay_recent_frame, _overlay_suggestion_frame
        try:
            root = tk.Tk()
            root.title("Grandpa Assistant")
            root.geometry("560x290")
            root.attributes("-topmost", True)
            root.configure(bg="#111827")
            root.resizable(False, False)

            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            x = (screen_width // 2) - 280
            y = max(60, (screen_height // 5))
            root.geometry(f"560x290+{x}+{y}")

            container = tk.Frame(root, bg="#111827", padx=16, pady=14)
            container.pack(fill="both", expand=True)

            label = tk.Label(
                container,
                text="Quick Command",
                fg="white",
                bg="#111827",
                font=("Segoe UI", 12, "bold"),
            )
            label.pack(anchor="w")

            entry = tk.Entry(
                container,
                font=("Segoe UI", 12),
                bg="#1f2937",
                fg="white",
                insertbackground="white",
                relief="flat",
            )
            entry.pack(fill="x", pady=(10, 6))

            hint = tk.Label(
                container,
                text="Press Enter to run, Esc to close",
                fg="#9ca3af",
                bg="#111827",
                font=("Segoe UI", 9),
            )
            hint.pack(anchor="w")

            suggestion_label = tk.Label(
                container,
                text="Quick Suggestions",
                fg="#d1d5db",
                bg="#111827",
                font=("Segoe UI", 10, "bold"),
            )
            suggestion_label.pack(anchor="w", pady=(14, 4))

            suggestion_frame = tk.Frame(container, bg="#111827")
            suggestion_frame.pack(fill="x", anchor="w")

            recent_label = tk.Label(
                container,
                text="Recent Commands",
                fg="#d1d5db",
                bg="#111827",
                font=("Segoe UI", 10, "bold"),
            )
            recent_label.pack(anchor="w", pady=(12, 4))

            recent_frame = tk.Frame(container, bg="#111827")
            recent_frame.pack(fill="x", anchor="w")

            def submit(_event=None):
                text = entry.get().strip()
                if not text:
                    return
                entry.delete(0, "end")
                root.withdraw()
                if _overlay_handler:
                    threading.Thread(
                        target=lambda: _overlay_handler(text), daemon=True
                    ).start()

            def close(_event=None):
                root.withdraw()

            root.bind("<Return>", submit)
            root.bind("<Escape>", close)
            root.protocol("WM_DELETE_WINDOW", close)

            _overlay_root = root
            _overlay_entry = entry
            _overlay_suggestion_frame = suggestion_frame
            _overlay_recent_frame = recent_frame
            _refresh_overlay_lists(suggestions=suggestions, recent_commands=recent_commands)
            entry.focus_force()
            root.mainloop()
        finally:
            _destroy_overlay()

    threading.Thread(target=worker, daemon=True).start()
    return True, "Quick command overlay opened."


def hide_quick_overlay():
    if _overlay_root is None:
        return False, "Quick command overlay is not open right now."

    try:
        _overlay_root.withdraw()
        return True, "Quick command overlay hidden."
    except Exception:
        return False, "I could not hide the quick command overlay right now."


def register_overlay_hotkey(
    callback,
    hotkey="ctrl+shift+space",
    suggestions=None,
    recent_commands=None,
    suggestions_provider=None,
    recent_provider=None,
):
    global _overlay_hotkey_handler, _overlay_hotkey_registered

    if keyboard is None or not hotkey:
        return False, "Keyboard hotkey support is not available."

    unregister_overlay_hotkey()

    def on_hotkey():
        if not _overlay_lock.acquire(blocking=False):
            return

        def worker():
            try:
                resolved_suggestions = (
                    suggestions_provider() if suggestions_provider else suggestions
                )
                resolved_recent = (
                    recent_provider() if recent_provider else recent_commands
                )
                show_quick_overlay(
                    callback,
                    suggestions=resolved_suggestions,
                    recent_commands=resolved_recent,
                )
            finally:
                _overlay_lock.release()

        threading.Thread(target=worker, daemon=True).start()

    try:
        _overlay_hotkey_handler = keyboard.add_hotkey(hotkey, on_hotkey)
        _overlay_hotkey_registered = hotkey
        return True, hotkey
    except Exception:
        _overlay_hotkey_handler = None
        _overlay_hotkey_registered = None
        return False, "I could not register the quick command overlay hotkey."


def unregister_overlay_hotkey():
    global _overlay_hotkey_handler, _overlay_hotkey_registered

    if keyboard is None:
        _overlay_hotkey_handler = None
        _overlay_hotkey_registered = None
        return False

    try:
        if _overlay_hotkey_handler is not None:
            keyboard.remove_hotkey(_overlay_hotkey_handler)
    except Exception:
        pass

    _overlay_hotkey_handler = None
    _overlay_hotkey_registered = None
    return True
