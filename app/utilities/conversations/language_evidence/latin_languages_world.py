"""Evidence of Filipino, Malay, Swahili and Uzbek, written in the Latin script."""

from app.utilities.conversations.language_evidence.language_evidence import (
    LanguageEvidence,
    letters,
    words,
)
from app.utilities.conversations.language_evidence.latin_languages import (
    ASCII_LETTERS,
)

# Uzbek writes "oʻ" and "gʻ" with a turned comma (U+02BB) or an apostrophe.
UZBEK_TURNED_COMMA: str = "ʻ"

WORLD_LATIN_LANGUAGE_EVIDENCE: dict[str, LanguageEvidence] = {
    "fil": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("ñ"),
        frozenset(),
        words(
            "ang ng mga sa na at ako ko ikaw po opo kumusta salamat paki gusto "
            "magpareserba mesa bukas ngayon magkano presyo pwede puwede tao "
            "oras gabi ba kayo namin"
        ),
    ),
    "ms": LanguageEvidence(
        "Latn",
        ASCII_LETTERS,
        frozenset(),
        words(
            "dan yang di ini itu saya awak anda untuk dengan tidak ada apa helo "
            "terima kasih meja esok berapa harga mahu nak tempah boleh selamat "
            "orang buka pukul malam"
        ),
    ),
    "sw": LanguageEvidence(
        "Latn",
        ASCII_LETTERS,
        frozenset(),
        words(
            "na ya wa kwa ni la za habari hujambo jambo mambo asante tafadhali "
            "nataka meza kesho leo bei gani ngapi ndiyo hapana karibu naweza "
            "watu saa usiku jioni"
        ),
    ),
    "uz": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters(UZBEK_TURNED_COMMA),
        letters(UZBEK_TURNED_COMMA),
        words(
            "va bu bir men siz salom assalomu alaykum rahmat iltimos stol band "
            "qilmoqchiman ertaga bugun qancha narxi ochiq mumkin kishi kishilik "
            "soat kechqurun bormi"
        ),
    ),
}
