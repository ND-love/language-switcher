import threading
import time

import keyboard

from .heuristics import evaluate_token


class AutoCorrectEngine:
    def __init__(self, status_callback=None):
        self._status_callback = status_callback
        self._hook = None
        self._enabled = False
        self._buffer = ""
        self._lock = threading.Lock()
        self._ignore_until = 0.0

        self._delimiters = {
            "space": " ",
            ".": ".",
            ",": ",",
            ";": ";",
            ":": ":",
            "!": "!",
            "?": "?",
            ")": ")",
        }

        self._reset_keys = {
            "left", "right", "up", "down",
            "home", "end", "page up", "page down",
            "esc", "escape", "insert", "delete",
        }

        self._modifier_keys = {
            "ctrl", "left ctrl", "right ctrl",
            "alt", "left alt", "right alt", "alt gr",
            "shift", "left shift", "right shift",
            "windows",
        }

    def _set_status(self, text: str):
        if self._status_callback:
            self._status_callback(text)

    def start(self):
        if self._enabled:
            return

        self._enabled = True
        self._hook = keyboard.hook(self._on_event, suppress=False)
        self._set_status("Автокоррекция включена")

    def stop(self):
        if self._hook is not None:
            try:
                keyboard.unhook(self._hook)
            except Exception:
                pass
            self._hook = None

        self._enabled = False
        self._buffer = ""
        self._set_status("Автокоррекция выключена")

    def _is_modifier_combo_active(self) -> bool:
        try:
            return (
                keyboard.is_pressed("ctrl")
                or keyboard.is_pressed("alt")
                or keyboard.is_pressed("windows")
            )
        except Exception:
            return False

    def _normalize_char(self, name: str) -> str | None:
        if not name:
            return None

        if len(name) == 1:
            return name

        return None

    def _reset_buffer(self):
        self._buffer = ""

    def _handle_backspace(self):
        if self._buffer:
            self._buffer = self._buffer[:-1]

    def _replace_last_token(self, original: str, corrected: str, delimiter: str):
        if not self._lock.acquire(blocking=False):
            return

        try:
            self._ignore_until = time.time() + 0.5

            backspaces = len(original) + (1 if delimiter else 0)
            for _ in range(backspaces):
                keyboard.send("backspace")
                time.sleep(0.005)

            keyboard.write(corrected, delay=0)

            if delimiter:
                keyboard.write(delimiter, delay=0)

            self._set_status(f"Автозамена: {original} -> {corrected}")
        finally:
            self._lock.release()

    def _finalize_token(self, delimiter_name: str):
        delimiter = self._delimiters.get(delimiter_name, "")
        token = self._buffer
        self._buffer = ""

        if not token:
            return

        decision = evaluate_token(token)
        if decision.should_replace:
            self._replace_last_token(token, decision.corrected, delimiter)

    def _on_event(self, event):
        if not self._enabled:
            return

        if event.event_type != "down":
            return

        now = time.time()
        if now < self._ignore_until:
            return

        name = event.name
        if not name:
            return

        low = name.lower()

        if low in self._modifier_keys:
            return

        if self._is_modifier_combo_active():
            self._reset_buffer()
            return

        if low == "backspace":
            self._handle_backspace()
            return

        if low in self._reset_keys:
            self._reset_buffer()
            return

        if low in self._delimiters:
            self._finalize_token(low)
            return

        ch = self._normalize_char(name)
        if ch is None:
            self._reset_buffer()
            return

        if ch.isalpha() or ch in "-'":
            self._buffer += ch
            if len(self._buffer) > 64:
                self._buffer = self._buffer[-64:]
        else:
            self._reset_buffer()