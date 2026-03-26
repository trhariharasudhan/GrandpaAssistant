import threading
import tkinter as tk

try:
    import keyboard
except ImportError:
    keyboard = None


_overlay_root = None
_overlay_entry = None
_overlay_handler = None
_overlay_hotkey_handler = None
_overlay_hotkey_registered = None
_overlay_lock = threading.Lock()


def _destroy_overlay():
    global _overlay_root, _overlay_entry

    if _overlay_root is None:
        return False

    try:
        _overlay_root.destroy()
    except Exception:
        pass

    _overlay_root = None
    _overlay_entry = None
    return True


def show_quick_overlay(on_submit):
    global _overlay_root, _overlay_entry, _overlay_handler

    _overlay_handler = on_submit

    if _overlay_root is not None:
        try:
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
        global _overlay_root, _overlay_entry
        try:
            root = tk.Tk()
            root.title("Grandpa Assistant")
            root.geometry("520x110")
            root.attributes("-topmost", True)
            root.configure(bg="#111827")
            root.resizable(False, False)

            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            x = (screen_width // 2) - 260
            y = max(60, (screen_height // 5))
            root.geometry(f"520x110+{x}+{y}")

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


def register_overlay_hotkey(callback, hotkey="ctrl+shift+space"):
    global _overlay_hotkey_handler, _overlay_hotkey_registered

    if keyboard is None or not hotkey:
        return False, "Keyboard hotkey support is not available."

    unregister_overlay_hotkey()

    def on_hotkey():
        if not _overlay_lock.acquire(blocking=False):
            return

        def worker():
            try:
                show_quick_overlay(callback)
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
