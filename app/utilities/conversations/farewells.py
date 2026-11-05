"""
Recognizing that a caller says goodbye, so the phone call can end.

Only short messages count ("Thanks, bye!"), never a longer sentence that
merely contains a farewell word.
"""

import re

MAX_FAREWELL_WORDS: int = 8
CJK_START: int = 0x2E80
FAREWELL_PHRASES: frozenset[str] = frozenset(
    {
        # English
        "bye",
        "goodbye",
        "good bye",
        "bye bye",
        "bye-bye",
        "see you",
        "have a nice day",
        # Russian, Ukrainian, Kazakh
        "пока",
        "до свидания",
        "всего доброго",
        "всего хорошего",
        "до встречи",
        "до побачення",
        "бувайте",
        "на все добре",
        "сау болыңыз",
        "көріскенше",
        # Georgian, Armenian, Azerbaijani, Turkish
        "ნახვამდის",
        "დროებით",
        "ցտեսություն",
        "հաջողություն",
        "sağ olun",
        "görüşənədək",
        "hələlik",
        "hoşça kal",
        "hoşçakal",
        "görüşürüz",
        "güle güle",
        # Hebrew, Arabic
        "להתראות",
        "ביי",
        "مع السلامة",
        "وداعا",
        "إلى اللقاء",
        # German, French, Spanish, Italian, Portuguese, Polish
        "tschüss",
        "auf wiedersehen",
        "auf wiederhören",
        "bis bald",
        "au revoir",
        "à bientôt",
        "adiós",
        "adios",
        "hasta luego",
        "arrivederci",
        "a presto",
        "tchau",
        "adeus",
        "até logo",
        "do widzenia",
        "do usłyszenia",
        # Chinese, Japanese
        "再见",
        "拜拜",
        "さようなら",
        "失礼します",
    }
)
WORD_PATTERN: re.Pattern[str] = re.compile(r"\w+(?:[-'’]\w+)*")


def is_farewell(text: str) -> bool:
    """True for a short message that says goodbye in a common language."""

    normalized_text: str = " ".join(WORD_PATTERN.findall(text.lower()))
    if normalized_text == "" or len(normalized_text.split()) > MAX_FAREWELL_WORDS:
        return False

    padded_text: str = f" {normalized_text} "
    for phrase in FAREWELL_PHRASES:
        if any(ord(character) >= CJK_START for character in phrase):
            if phrase in normalized_text:
                return True
        elif f" {phrase} " in padded_text:
            return True

    return False
