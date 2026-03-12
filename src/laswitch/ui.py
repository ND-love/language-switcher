import sys
import threading

import keyboard
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from .manual_switcher import LayoutSwitcherLogic
from .utils import HK_TRANS_DICT, load_settings, save_settings


class HotkeyRecorder(QThread):
    finished_recording = Signal(str)

    def run(self):
        recorded = keyboard.read_hotkey(suppress=False)
        recorded = recorded.translate(HK_TRANS_DICT)

        modifiers = [
            "ctrl", "alt", "shift", "windows",
            "left ctrl", "right ctrl",
            "left alt", "right alt",
            "left shift", "right shift",
        ]
        keys = recorded.split("+")

        if all(k.lower() in modifiers for k in keys):
            self.finished_recording.emit("")
        else:
            self.finished_recording.emit(recorded)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LaSwitch")
        self.setFixedSize(360, 240)

        self.settings = load_settings()
        self.logic = LayoutSwitcherLogic(status_callback=self.set_status)
        self.logic.mode = self.settings["mode"]

        self.hotkey_hook = None
        self.is_recording = False
        self.really_quit = False

        self.setup_ui()
        self.setup_tray()
        self.register_hotkey(self.settings["hotkey"])

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        hk_layout = QHBoxLayout()
        self.lbl_hotkey_title = QLabel("Горячая клавиша:")
        self.lbl_hotkey_value = QLabel(f"<b>{self.settings['hotkey'].upper()}</b>")
        hk_layout.addWidget(self.lbl_hotkey_title)
        hk_layout.addWidget(self.lbl_hotkey_value)
        layout.addLayout(hk_layout)

        self.btn_record = QPushButton("Записать сочетание")
        self.btn_record.clicked.connect(self.start_recording)
        layout.addWidget(self.btn_record)

        layout.addWidget(QLabel("Режим работы:"))

        self.radio_selection = QRadioButton("По выделению")
        self.radio_all = QRadioButton("Всё поле")

        if self.settings["mode"] == "all":
            self.radio_all.setChecked(True)
        else:
            self.radio_selection.setChecked(True)

        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.radio_selection)
        self.mode_group.addButton(self.radio_all)

        self.radio_selection.toggled.connect(self.change_mode)

        layout.addWidget(self.radio_selection)
        layout.addWidget(self.radio_all)

        self.btn_hide = QPushButton("Свернуть в трей")
        self.btn_hide.clicked.connect(self.hide)
        layout.addWidget(self.btn_hide)

        self.btn_exit = QPushButton("Выход")
        self.btn_exit.clicked.connect(self.exit_app)
        layout.addWidget(self.btn_exit)

        self.statusBar().showMessage("Готово к работе")

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon = self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
        self.tray_icon.setIcon(icon)

        tray_menu = QMenu()

        show_action = QAction("Показать окно", self)
        show_action.triggered.connect(self.showNormal)
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()

        self.mode_sel_action = QAction("Режим: По выделению", self, checkable=True)
        self.mode_sel_action.triggered.connect(lambda: self.set_mode_from_tray("selection"))

        self.mode_all_action = QAction("Режим: Всё поле", self, checkable=True)
        self.mode_all_action.triggered.connect(lambda: self.set_mode_from_tray("all"))

        self.update_tray_menu_checks()
        tray_menu.addAction(self.mode_sel_action)
        tray_menu.addAction(self.mode_all_action)
        tray_menu.addSeparator()

        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self.exit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.on_tray_click)

    def on_tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()

    def update_tray_menu_checks(self):
        is_sel = self.settings["mode"] == "selection"
        self.mode_sel_action.setChecked(is_sel)
        self.mode_all_action.setChecked(not is_sel)

    def change_mode(self):
        mode = "selection" if self.radio_selection.isChecked() else "all"
        self.settings["mode"] = mode
        self.logic.mode = mode
        save_settings(self.settings)
        self.update_tray_menu_checks()
        self.set_status(f"Режим изменён: {mode}")

    def set_mode_from_tray(self, mode):
        self.settings["mode"] = mode
        self.logic.mode = mode
        save_settings(self.settings)
        self.update_tray_menu_checks()

        if mode == "selection":
            self.radio_selection.setChecked(True)
        else:
            self.radio_all.setChecked(True)

    def start_recording(self):
        if self.is_recording:
            return

        self.remove_current_hotkey()
        self.is_recording = True
        self.btn_record.setText("Нажмите сочетание...")
        self.btn_record.setEnabled(False)
        self.set_status("Ожидание ввода хоткея...")

        self.recorder_thread = HotkeyRecorder()
        self.recorder_thread.finished_recording.connect(self.finish_recording)
        self.recorder_thread.start()

    def finish_recording(self, new_hotkey):
        self.is_recording = False
        self.btn_record.setText("Записать сочетание")
        self.btn_record.setEnabled(True)

        if new_hotkey == "":
            QMessageBox.warning(
                self,
                "Ошибка",
                "Сочетание должно содержать хотя бы одну основную клавишу.",
            )
            self.register_hotkey(self.settings["hotkey"])
            self.set_status("Ошибка записи")
        else:
            self.settings["hotkey"] = new_hotkey
            self.lbl_hotkey_value.setText(f"<b>{new_hotkey.upper()}</b>")
            save_settings(self.settings)
            self.register_hotkey(new_hotkey)
            self.set_status(f"Сохранён новый хоткей: {new_hotkey}")

    def remove_current_hotkey(self):
        if self.hotkey_hook:
            try:
                keyboard.remove_hotkey(self.hotkey_hook)
            except Exception:
                pass
            self.hotkey_hook = None

    def trigger_action(self):
        threading.Thread(target=self.logic.execute_switch, daemon=True).start()

    def register_hotkey(self, hotkey_str):
        self.remove_current_hotkey()
        try:
            self.hotkey_hook = keyboard.add_hotkey(
                hotkey_str,
                self.trigger_action,
                suppress=True
            )
        except Exception:
            self.set_status("Ошибка регистрации хоткея")

    def set_status(self, text: str):
        self.statusBar().showMessage(text)

    def closeEvent(self, event):
        if not self.really_quit:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "LaSwitch",
                "Приложение работает в фоне",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
        else:
            event.accept()

    def exit_app(self):
        self.remove_current_hotkey()
        self.really_quit = True
        self.tray_icon.hide()
        QApplication.quit()


def run_app():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())