"""
Which language a writing system points to on its own.

A script used by one language of the assistant's world names it at once
(Georgian letters are Georgian). A script shared by many languages names
its most widely written one when the text gives no other evidence and no
business language uses the script. Neutral words are typed the same in
chats of every language and say nothing about it.
"""

import re

# Scripts that, among the languages customers write to businesses in, one
# language uses (ISO 15924 -> language). Han is Chinese unless kana appear
# (then the script is "Kana", Japanese).
SINGLE_LANGUAGE_SCRIPTS: dict[str, str] = {
    "Geor": "ka",
    "Armn": "hy",
    "Hebr": "he",
    "Grek": "el",
    "Thai": "th",
    "Laoo": "lo",
    "Khmr": "km",
    "Mymr": "my",
    "Tibt": "bo",
    "Ethi": "am",
    "Beng": "bn",
    "Guru": "pa",
    "Gujr": "gu",
    "Orya": "or",
    "Taml": "ta",
    "Telu": "te",
    "Knda": "kn",
    "Mlym": "ml",
    "Sinh": "si",
    "Thaa": "dv",
    "Hang": "ko",
    "Kana": "ja",
    "Hani": "zh",
}
# Scripts several languages share -> the language assumed without evidence.
SHARED_SCRIPT_DEFAULTS: dict[str, str] = {
    "Latn": "en",
    "Cyrl": "ru",
    "Arab": "ar",
    "Deva": "hi",
}
# Languages a Han text may be written in: Japanese can be all kanji.
HAN_LANGUAGES: tuple[str, ...] = ("zh", "ja")
LATIN_SCRIPT: str = "Latn"
# Words typed alike in chats of any language: they keep the conversation's
# language ("ok" never turns a Russian conversation into English).
NEUTRAL_WORDS: frozenset[str] = frozenset(
    {
        "ok",
        "okay",
        "okey",
        "oke",
        "oki",
        "okk",
        "k",
        "kk",
        "lol",
        "omg",
        "wow",
        "xd",
        "hm",
        "hmm",
        "mm",
        "mmm",
        "ок",
        "окей",
        "оке",
        "ოკ",
        "ოკეი",
    }
)
LAUGHTER_PATTERN: re.Pattern[str] = re.compile(
    r"^(?:[ah]{3,}|[eh]{3,}|[ха]{3,}|[хе]{3,}|(?:ჰა){2,}|ח{2,}|ه{3,})$"
)


def is_neutral_word(word: str) -> bool:
    """ "ok", "lol", "hahaha", "хаха": no language can be read from it."""

    return word in NEUTRAL_WORDS or LAUGHTER_PATTERN.fullmatch(word) is not None
