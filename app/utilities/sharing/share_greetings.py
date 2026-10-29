"""
The greeting a tagged wa.me link fills in for the customer, in the
business's greeting language (its base language, else English), before
the link's code ("Здравствуйте! (#qr-tables)").
"""

from app.schemas.typings.localization.constrained_strings import LanguageTag

DEFAULT_GREETING: str = "Hello!"
GREETINGS: dict[str, str] = {
    "ar": "مرحبًا!",
    "az": "Salam!",
    "de": "Hallo!",
    "el": "Γεια σας!",
    "en": DEFAULT_GREETING,
    "es": "¡Hola!",
    "fa": "سلام!",
    "fr": "Bonjour !",
    "he": "שלום!",
    "hi": "नमस्ते!",
    "hy": "Բարև Ձեզ!",
    "it": "Buongiorno!",
    "ja": "こんにちは！",
    "ka": "გამარჯობა!",
    "kk": "Сәлеметсіз бе!",
    "ko": "안녕하세요!",
    "nl": "Hallo!",
    "pl": "Dzień dobry!",
    "pt": "Olá!",
    "ro": "Bună ziua!",
    "ru": "Здравствуйте!",
    "tr": "Merhaba!",
    "uk": "Добрий день!",
    "uz": "Assalomu alaykum!",
    "zh": "你好！",
}


def greeting_in(language: LanguageTag | None) -> str:
    """The greeting in the language's base language, else in English."""

    if language is None:
        return DEFAULT_GREETING

    return GREETINGS.get(str(language).split("-")[0].lower(), DEFAULT_GREETING)
