"""
A linter of service messages (booking confirmations, reminders, a
deposit's line and reminders): such a message carries no promotion, so it
never turns into marketing without consent (Codice privacy art. 130) and
never breaks Meta's rule that a utility template promotes nothing. It
flags promotional words in the platform's customer languages, anything
shaped like a discount code, and links written into the text (a link a
service message needs comes from the platform as a `{placeholder}`).
"""

import re
from collections.abc import Iterator
from types import ModuleType

from app.schemas.dto.localization import LocalizedText

# Lowercase stems: a word starting with one of them is promotional.
PROMOTIONAL_STEMS: tuple[str, ...] = (
    # English
    "discount", "promo", "offer", "coupon", "voucher", "deal", "sale",
    "% off", "special price", "free gift", "limited time",
    # Italian
    "sconto", "sconti", "offert", "promozion", "saldi", "buono sconto",
    # Russian, Ukrainian
    "скидк", "акци", "промокод", "знижк", "пропозиці",
    # German, French, Spanish, Portuguese
    "rabatt", "angebot", "remise", "réduction", "descuento", "oferta",
    "desconto",
    # Turkish, Polish
    "indirim", "kampanya", "rabat", "zniżk", "promocj",
    # Georgian, Armenian, Hebrew, Arabic
    "ფასდაკლებ", "აქცი", "զեղչ", "הנחה", "מבצע", "خصم", "عرض خاص",
)  # fmt: skip
# Words a service message needs although a stem above starts them.
SERVICE_WORDS: frozenset[str] = frozenset({"акционер"})
DISCOUNT_CODE: re.Pattern[str] = re.compile(
    r"\b(?=[A-Z0-9]*\d)(?=[A-Z0-9]*[A-Z])[A-Z0-9]{5,}\b"
)
LINK: re.Pattern[str] = re.compile(r"https?://|www\.", re.IGNORECASE)
PLACEHOLDER: re.Pattern[str] = re.compile(r"\{[a-z_]+\}")


def word_start(stem: str) -> str:
    """The stem where a word starts ("% off" anywhere, since "20% off")."""

    return rf"(?<!\w){re.escape(stem)}" if stem[0].isalnum() else re.escape(stem)


def promotional_findings(text: str) -> list[str]:
    """What makes this text promotional (empty: a clean service text)."""

    plain: str = PLACEHOLDER.sub(" ", text)
    lowered: str = plain.lower()
    findings: list[str] = [
        f"promotional word {stem!r}"
        for stem in PROMOTIONAL_STEMS
        if re.search(word_start(stem), lowered)
        and not any(word in lowered for word in SERVICE_WORDS if word.startswith(stem))
    ]
    findings.extend(f"discount code {code!r}" for code in DISCOUNT_CODE.findall(plain))
    if LINK.search(plain):
        findings.append("a link written into the text")
    return findings


def localized_texts(module: ModuleType) -> Iterator[tuple[str, LocalizedText]]:
    """Every localized text a module defines at its top level."""

    for name, value in vars(module).items():
        if isinstance(value, LocalizedText):
            yield name, value


def lint_module(module: ModuleType) -> dict[str, list[str]]:
    """`TEXT_NAME[language]` -> findings, for every flagged value."""

    return {
        f"{name}[{language}]": findings
        for name, text in localized_texts(module)
        for language, value in text.values.items()
        if (findings := promotional_findings(str(value)))
    }
