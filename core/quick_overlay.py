import json
import os
import threading
import tkinter as tk
from tkinter import ttk

try:
    import keyboard
except ImportError:
    keyboard = None


_overlay_root = None
_overlay_entry = None
_overlay_handler = None
_overlay_recent_frame = None
_overlay_action_frame = None
_overlay_suggestion_frame = None
_overlay_context_frame = None
_overlay_hotkey_handler = None
_overlay_hotkey_registered = None
_overlay_lock = threading.Lock()
_overlay_all_suggestions = None
_overlay_all_recent_commands = None
_overlay_all_recent_actions = None
_overlay_all_context_items = None
_STATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "overlay_state.json",
)


def _load_overlay_state():
    if not os.path.exists(_STATE_PATH):
        return {"pinned_commands": []}
    try:
        with open(_STATE_PATH, "r", encoding="utf-8") as file:
            state = json.load(file)
    except Exception:
        return {"pinned_commands": []}
    state.setdefault("pinned_commands", [])
    return state


def _save_overlay_state(state):
    os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
    with open(_STATE_PATH, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=4)


def get_pinned_commands():
    return [item for item in _load_overlay_state().get("pinned_commands", []) if item]


def pin_overlay_command(command_text):
    command_text = (command_text or "").strip().lower()
    if not command_text:
        return False, "Tell me which command you want to pin."

    state = _load_overlay_state()
    pinned = [item.strip().lower() for item in state.get("pinned_commands", []) if item]
    if command_text in pinned:
        return False, f"{command_text} is already pinned."

    pinned.insert(0, command_text)
    state["pinned_commands"] = pinned[:8]
    _save_overlay_state(state)
    return True, f"Pinned {command_text} to the quick overlay."


def unpin_overlay_command(command_text):
    command_text = (command_text or "").strip().lower()
    if not command_text:
        return False, "Tell me which command you want to unpin."

    state = _load_overlay_state()
    pinned = [item.strip().lower() for item in state.get("pinned_commands", []) if item]
    if command_text not in pinned:
        return False, f"{command_text} is not pinned right now."

    pinned = [item for item in pinned if item != command_text]
    state["pinned_commands"] = pinned
    _save_overlay_state(state)
    return True, f"Unpinned {command_text} from the quick overlay."


def list_pinned_commands():
    pinned = get_pinned_commands()
    if not pinned:
        return "You do not have any pinned overlay commands right now."
    return "Pinned overlay commands: " + " | ".join(
        f"{index}. {item}" for index, item in enumerate(pinned, start=1)
    )


def move_pinned_command(command_text, direction):
    command_text = (command_text or "").strip().lower()
    direction = (direction or "").strip().lower()
    if not command_text:
        return False, "Tell me which pinned command you want to move."
    if direction not in {"up", "down", "top", "bottom"}:
        return False, "Use up, down, top, or bottom for pinned command move."

    state = _load_overlay_state()
    pinned = [item.strip().lower() for item in state.get("pinned_commands", []) if item]
    if command_text not in pinned:
        return False, f"{command_text} is not pinned right now."

    index = pinned.index(command_text)
    if direction == "up" and index > 0:
        pinned[index - 1], pinned[index] = pinned[index], pinned[index - 1]
    elif direction == "down" and index < len(pinned) - 1:
        pinned[index + 1], pinned[index] = pinned[index], pinned[index + 1]
    elif direction == "top":
        pinned.insert(0, pinned.pop(index))
    elif direction == "bottom":
        pinned.append(pinned.pop(index))

    state["pinned_commands"] = pinned
    _save_overlay_state(state)
    return True, f"Moved {command_text} {direction} in pinned commands."


def _destroy_overlay():
    global _overlay_root, _overlay_entry, _overlay_recent_frame, _overlay_action_frame, _overlay_suggestion_frame, _overlay_context_frame

    if _overlay_root is None:
        return False

    try:
        _overlay_root.destroy()
    except Exception:
        pass

    _overlay_root = None
    _overlay_entry = None
    _overlay_recent_frame = None
    _overlay_action_frame = None
    _overlay_suggestion_frame = None
    _overlay_context_frame = None
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


def _normalize_chip_item(item):
    if isinstance(item, (tuple, list)) and len(item) >= 2:
        return str(item[0]), str(item[1])
    return str(item), str(item)


def _filter_chip_collections(query, suggestions, recent_commands, context_items, recent_actions):
    query = (query or "").strip().lower()
    if not query:
        return suggestions, recent_commands, context_items

    def matches(item):
        label, command_text = _normalize_chip_item(item)
        searchable = f"{label} {command_text}".lower()
        return query in searchable

    filtered_context = [item for item in (context_items or []) if matches(item)]
    filtered_recent = [item for item in (recent_commands or []) if query in str(item).lower()]
    filtered_actions = [item for item in (recent_actions or []) if query in str(item).lower()]

    if isinstance(suggestions, dict):
        filtered_suggestions = {}
        for category, items in suggestions.items():
            matched_items = [item for item in items if matches(item)]
            if matched_items:
                filtered_suggestions[category] = matched_items
    else:
        filtered_suggestions = [item for item in (suggestions or []) if matches(item)]

    return filtered_suggestions, filtered_recent, filtered_context, filtered_actions


def _refresh_overlay_lists(suggestions=None, recent_commands=None, context_items=None, recent_actions=None):
    if (
        _overlay_recent_frame is None
        or _overlay_action_frame is None
        or _overlay_suggestion_frame is None
        or _overlay_context_frame is None
        or _overlay_handler is None
    ):
        return

    if isinstance(_overlay_suggestion_frame, dict):
        for frame in _overlay_suggestion_frame.values():
            _clear_frame(frame)
    else:
        _clear_frame(_overlay_suggestion_frame)
    _clear_frame(_overlay_recent_frame)
    _clear_frame(_overlay_action_frame)
    _clear_frame(_overlay_context_frame)

    suggestions = suggestions or {}
    recent_commands = recent_commands or []
    recent_actions = recent_actions or []
    context_items = context_items or []

    for index, item in enumerate(context_items):
        label, command_text = _normalize_chip_item(item)
        chip = _make_chip(
            _overlay_context_frame,
            label,
            command_text,
            _overlay_handler,
            bg="#7c3aed",
        )
        chip.grid(row=index // 2, column=index % 2, padx=4, pady=4, sticky="w")

    if isinstance(suggestions, dict):
        for category_name, items in suggestions.items():
            frame = _overlay_suggestion_frame.get(category_name)
            if frame is None:
                continue
            for index, item in enumerate(items):
                label, command_text = _normalize_chip_item(item)
                chip = _make_chip(
                    frame,
                    label,
                    command_text,
                    _overlay_handler,
                    bg="#0f766e",
                )
                chip.grid(row=index // 2, column=index % 2, padx=4, pady=4, sticky="w")
    else:
        target_frame = (
            next(iter(_overlay_suggestion_frame.values()))
            if isinstance(_overlay_suggestion_frame, dict)
            else _overlay_suggestion_frame
        )
        for index, item in enumerate(suggestions):
            label, command_text = _normalize_chip_item(item)
            chip = _make_chip(
                target_frame,
                label,
                command_text,
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

    for index, item in enumerate(recent_actions):
        chip = _make_chip(
            _overlay_action_frame,
            item,
            item,
            _overlay_handler,
            bg="#7c2d12",
        )
        chip.grid(row=index // 2, column=index % 2, padx=4, pady=4, sticky="w")


def show_quick_overlay(on_submit, suggestions=None, recent_commands=None, context_items=None, recent_actions=None):
    global _overlay_root, _overlay_entry, _overlay_handler, _overlay_recent_frame
    global _overlay_action_frame, _overlay_suggestion_frame, _overlay_context_frame
    global _overlay_all_suggestions, _overlay_all_recent_commands, _overlay_all_recent_actions, _overlay_all_context_items

    _overlay_handler = on_submit
    _overlay_all_suggestions = suggestions or {}
    _overlay_all_recent_commands = recent_commands or []
    _overlay_all_recent_actions = recent_actions or recent_commands or []
    _overlay_all_context_items = context_items or []

    if _overlay_root is not None:
        try:
            _refresh_overlay_lists(
                suggestions=_overlay_all_suggestions,
                recent_commands=_overlay_all_recent_commands,
                recent_actions=_overlay_all_recent_actions,
                context_items=_overlay_all_context_items,
            )
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
        global _overlay_root, _overlay_entry, _overlay_recent_frame, _overlay_action_frame, _overlay_suggestion_frame, _overlay_context_frame
        try:
            root = tk.Tk()
            root.title("Grandpa Assistant")
            root.geometry("620x430")
            root.attributes("-topmost", True)
            root.configure(bg="#111827")
            root.resizable(False, False)

            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            x = (screen_width // 2) - 310
            y = max(60, (screen_height // 5))
            root.geometry(f"620x430+{x}+{y}")

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

            context_label = tk.Label(
                container,
                text="Daily Context",
                fg="#d1d5db",
                bg="#111827",
                font=("Segoe UI", 10, "bold"),
            )
            context_label.pack(anchor="w", pady=(14, 4))

            context_frame = tk.Frame(container, bg="#111827")
            context_frame.pack(fill="x", anchor="w")

            suggestion_label = tk.Label(
                container,
                text="Quick Suggestions",
                fg="#d1d5db",
                bg="#111827",
                font=("Segoe UI", 10, "bold"),
            )
            suggestion_label.pack(anchor="w", pady=(14, 4))

            notebook = ttk.Notebook(container)
            notebook.pack(fill="both", expand=False, anchor="w")

            categories = (
                list(suggestions.keys())
                if isinstance(suggestions, dict) and suggestions
                else ["Suggestions"]
            )
            suggestion_frames = {}
            for category in categories:
                tab_frame = tk.Frame(notebook, bg="#111827")
                notebook.add(tab_frame, text=category)
                suggestion_frames[category] = tab_frame

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

            action_label = tk.Label(
                container,
                text="Recent Actions",
                fg="#d1d5db",
                bg="#111827",
                font=("Segoe UI", 10, "bold"),
            )
            action_label.pack(anchor="w", pady=(12, 4))

            action_frame = tk.Frame(container, bg="#111827")
            action_frame.pack(fill="x", anchor="w")

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

            def on_change(_event=None):
                filtered_suggestions, filtered_recent, filtered_context, filtered_actions = _filter_chip_collections(
                    entry.get(),
                    _overlay_all_suggestions,
                    _overlay_all_recent_commands,
                    _overlay_all_context_items,
                    _overlay_all_recent_actions,
                )
                _refresh_overlay_lists(
                    suggestions=filtered_suggestions,
                    recent_commands=filtered_recent,
                    recent_actions=filtered_actions,
                    context_items=filtered_context,
                )

            root.bind("<Return>", submit)
            root.bind("<Escape>", close)
            entry.bind("<KeyRelease>", on_change)
            root.protocol("WM_DELETE_WINDOW", close)

            _overlay_root = root
            _overlay_entry = entry
            _overlay_context_frame = context_frame
            _overlay_suggestion_frame = suggestion_frames
            _overlay_recent_frame = recent_frame
            _overlay_action_frame = action_frame
            _refresh_overlay_lists(
                suggestions=_overlay_all_suggestions,
                recent_commands=_overlay_all_recent_commands,
                recent_actions=_overlay_all_recent_actions,
                context_items=_overlay_all_context_items,
            )
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


def is_quick_overlay_open():
    if _overlay_root is None:
        return False

    try:
        return _overlay_root.state() != "withdrawn"
    except Exception:
        return True


def register_overlay_hotkey(
    callback,
    hotkey="ctrl+shift+space",
    suggestions=None,
    recent_commands=None,
    recent_actions=None,
    context_items=None,
    suggestions_provider=None,
    recent_provider=None,
    recent_actions_provider=None,
    context_provider=None,
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
                resolved_actions = (
                    recent_actions_provider() if recent_actions_provider else recent_actions
                )
                resolved_context = (
                    context_provider() if context_provider else context_items
                )
                show_quick_overlay(
                    callback,
                    suggestions=resolved_suggestions,
                    recent_commands=resolved_recent,
                    recent_actions=resolved_actions,
                    context_items=resolved_context,
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
