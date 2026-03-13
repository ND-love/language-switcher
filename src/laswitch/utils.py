import json
import os

EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,./QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?`~@#$%^&*"
RU = "йцукенгшщзхъфывапролджэячсмитьбю.ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,ёЁ\"№;%:?*"

EN_TO_RU = str.maketrans(EN, RU)
RU_TO_EN = str.maketrans(RU, EN)

HK_RU = "йцукенгшщзхъфывапролджэячсмитьбюё"
HK_EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,.`"
HK_TRANS_DICT = str.maketrans(HK_RU, HK_EN)

APPDATA = os.getenv("APPDATA", "")
SETTINGS_DIR = os.path.join(APPDATA, "LaSwitch")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")
LOGS_DIR = os.path.join(APPDATA, "LaSwitch", "logs")
LOG_FILE = os.path.join(LOGS_DIR, "laswitch.log")

DEFAULT_SETTINGS = {
    "hotkey": "f8",
    "mode": "all",
    "auto_correct_enabled": False,
}


def ensure_app_dirs():
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)


def load_settings():
    ensure_app_dirs()

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    result = DEFAULT_SETTINGS.copy()
                    result.update(data)
                    return result
        except Exception:
            pass

    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict):
    ensure_app_dirs()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def detect_conversion_direction(text: str) -> str:
    ru_letters = sum(
        1 for c in text
        if c in "йцукенгшщзхъфывапролджэячсмитьбюёЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮЁ"
    )
    en_letters = sum(
        1 for c in text
        if c in "qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM"
    )

    return "ru_to_en" if ru_letters > en_letters else "en_to_ru"


def convert_text(text: str) -> str:
    direction = detect_conversion_direction(text)
    if direction == "ru_to_en":
        return text.translate(RU_TO_EN)
    return text.translate(EN_TO_RU)