from dataclasses import dataclass

from .utils import EN_TO_RU, RU_TO_EN


RU_ALPHA = set("йцукенгшщзхъфывапролджэячсмитьбюё")
EN_ALPHA = set("qwertyuiopasdfghjklzxcvbnm")

RU_VOWELS = set("аеёиоуыэюя")
EN_VOWELS = set("aeiouy")

COMMON_RU = {
    "привет", "пока", "как", "дела", "да", "нет", "это", "что", "где", "тут",
    "там", "тебя", "меня", "можно", "нужно", "спасибо", "пожалуйста", "я",
    "ты", "он", "она", "мы", "они", "сейчас", "потом", "очень", "хорошо",
    "плохо", "день", "ночь", "утро", "вечер", "работа", "дом", "программа",
    "текст", "окно", "приветик", "даниил", "дима", "настя", "абракадабра",
}

COMMON_EN = {
    "hello", "hi", "john", "i", "am", "you", "he", "she", "we", "they", "yes",
    "no", "thanks", "please", "text", "window", "program", "home", "work",
    "good", "bad", "morning", "night", "later", "now", "daniil", "name",
    "what", "where", "why", "how", "test", "switch", "layout",
}

RU_BIGRAMS = {
    "ст", "но", "то", "на", "ен", "ни", "ов", "ра", "ко", "пр", "по", "го",
    "ро", "та", "во", "не", "ло", "ли", "ре", "ве", "ка", "ри", "пр", "ив",
    "ет", "де", "ла", "мо", "жн", "уж", "но", "сп", "ас", "иб", "бо",
}

EN_BIGRAMS = {
    "th", "he", "in", "er", "an", "re", "on", "at", "en", "nd", "ou", "ll",
    "el", "lo", "ha", "hi", "am", "jo", "oh", "hn", "te", "xt", "sw", "it",
    "ch", "la", "ay", "yo", "ou", "no", "ow",
}

SKIP_SUBSTRINGS = (
    "://", "\\", "/", "@", "_", "=", "#", "%", ".py", ".exe", ".com", ".ru"
)


@dataclass
class Decision:
    should_replace: bool
    corrected: str
    target_lang: str | None
    reason: str


def _count_lang_chars(token: str):
    ru = sum(1 for ch in token.lower() if ch in RU_ALPHA)
    en = sum(1 for ch in token.lower() if ch in EN_ALPHA)
    return ru, en


def _token_kind(token: str) -> str | None:
    ru, en = _count_lang_chars(token)

    if ru > 0 and en == 0:
        return "ru"
    if en > 0 and ru == 0:
        return "en"
    return None


def _looks_like_code_or_service(token: str) -> bool:
    low = token.lower()

    if any(part in low for part in SKIP_SUBSTRINGS):
        return True

    if any(ch.isdigit() for ch in token):
        return True

    if token.isupper() and len(token) >= 2:
        return True

    return False


def _preserve_case(src: str, dst: str) -> str:
    if src.isupper():
        return dst.upper()
    if src[:1].isupper() and src[1:].islower():
        return dst.capitalize()
    return dst


def _score_ru(word: str) -> int:
    w = word.lower()
    score = 0

    if w in COMMON_RU:
        score += 12

    for i in range(len(w) - 1):
        if w[i:i + 2] in RU_BIGRAMS:
            score += 2

    vowel_count = sum(1 for ch in w if ch in RU_VOWELS)
    if vowel_count > 0:
        score += 2

    if "ъъ" in w or "ьы" in w or "йй" in w:
        score -= 4

    return score


def _score_en(word: str) -> int:
    w = word.lower()
    score = 0

    if w in COMMON_EN:
        score += 12

    for i in range(len(w) - 1):
        if w[i:i + 2] in EN_BIGRAMS:
            score += 2

    vowel_count = sum(1 for ch in w if ch in EN_VOWELS)
    if vowel_count > 0:
        score += 2

    if "qq" in w or "jj" in w or "zxq" in w:
        score -= 4

    return score


def evaluate_token(token: str) -> Decision:
    token = token.strip()
    if not token:
        return Decision(False, token, None, "empty")

    if len(token) < 3:
        return Decision(False, token, None, "too_short")

    if _looks_like_code_or_service(token):
        return Decision(False, token, None, "service_or_code")

    kind = _token_kind(token)
    if kind is None:
        return Decision(False, token, None, "mixed_or_unknown")

    if kind == "ru":
        converted = token.translate(RU_TO_EN)
        original_score = _score_ru(token)
        converted_score = _score_en(converted)
        target_lang = "en"
    else:
        converted = token.translate(EN_TO_RU)
        original_score = _score_en(token)
        converted_score = _score_ru(converted)
        target_lang = "ru"

    converted = _preserve_case(token, converted)

    diff = converted_score - original_score
    threshold = 5 if len(token) <= 4 else 4

    if diff >= threshold:
        return Decision(True, converted, target_lang, f"score_diff={diff}")

    return Decision(False, token, None, f"score_diff={diff}")