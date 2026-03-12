import threading
import time

import keyboard
import pyperclip

from .utils import convert_text


class LayoutSwitcherLogic:
    def __init__(self, status_callback=None):
        self.mode = "all"
        self._status_callback = status_callback
        self._lock = threading.Lock()

    def set_status(self, text: str):
        if self._status_callback:
            self._status_callback(text)

    def execute_switch(self):
        if not self._lock.acquire(blocking=False):
            return

        try:
            self.set_status("Обработка текста...")

            keyboard.release("ctrl")
            keyboard.release("alt")
            keyboard.release("shift")
            time.sleep(0.02)

            if self.mode == "all":
                keyboard.press("ctrl")
                keyboard.press(30)  # scan-code A
                keyboard.release(30)
                keyboard.release("ctrl")
                time.sleep(0.07)

            try:
                pyperclip.copy("")
            except Exception:
                pass

            keyboard.press("ctrl")
            keyboard.press("insert")
            keyboard.release("insert")
            keyboard.release("ctrl")

            text = ""
            for _ in range(20):
                time.sleep(0.015)
                try:
                    text = pyperclip.paste()
                except Exception:
                    continue
                if text:
                    break

            if not text:
                self.set_status("Не удалось получить текст")
                return

            new_text = convert_text(text)

            if new_text != text:
                keyboard.write(new_text, delay=0)
                self.set_status("Готово")
            else:
                self.set_status("Нечего менять")

        except Exception as e:
            self.set_status(f"Ошибка: {e}")
        finally:
            self._lock.release()