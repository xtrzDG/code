"""
Public chat addresses (`/c/{slug}`): the words the platform keeps for its
own pages, and the addresses suggested for a business from its name.
"""

import unicodedata

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.sharing.constrained_strings import BusinessPublicSlug
from app.utilities.sharing.slug_transliteration import LETTER_SPELLINGS

# Pages of the platform and words that would mislead visitors.
RESERVED_SLUGS: frozenset[str] = frozenset(
    {
        "about", "admin", "api", "app", "assistant", "assistant-workshop",
        "billing", "blog", "c", "chat", "contact", "demo", "docs", "help",
        "login", "logout", "new", "official", "privacy", "security",
        "settings", "static", "status", "support", "terms", "test", "widget",
        "workshop", "www",
    }
)  # fmt: skip
# Words longer than this are cut at a word boundary where possible.
MAX_BASE_LENGTH: int = 32
# How many numbered variants ("cafe-batumi-2" ...) are tried before the
# fallback built from the business id.
NUMBERED_VARIANTS: int = 8
FALLBACK_PREFIX: str = "chat"
FALLBACK_ID_CHARACTERS: int = 8


def is_reserved_slug(slug: BusinessPublicSlug) -> bool:
    return str(slug) in RESERVED_SLUGS


def spell_in_latin(name: str) -> str:
    """
    The name in lowercase Latin letters and digits, every other run of
    characters a single hyphen ("Café Батуми" gives "cafe-batumi").
    """

    spelled: list[str] = []
    for character in name.lower():
        if character in LETTER_SPELLINGS:
            spelled.append(LETTER_SPELLINGS[character])
            continue

        latin: str = "".join(
            part
            for part in unicodedata.normalize("NFKD", character)
            if part.isascii() and part.isalnum()
        ).lower()
        spelled.append(latin or "-")

    words: list[str] = [word for word in "".join(spelled).split("-") if word]
    return "-".join(words)


def shorten(text: str, max_length: int) -> str:
    """At most `max_length` characters, cut after a whole word if one fits."""

    if len(text) <= max_length:
        return text

    cut: str = text[:max_length]
    if "-" in cut:
        cut = cut[: cut.rindex("-")]

    return cut.strip("-")


def suggest_slugs(
    business_name: BusinessName,
    business_id: BusinessId,
) -> list[BusinessPublicSlug]:
    """
    Addresses to try for a business, best first: its name in Latin letters,
    then numbered variants of it, and last one made from the business id
    (always valid, practically never taken).
    """

    candidates: list[BusinessPublicSlug] = []
    base: str = shorten(spell_in_latin(str(business_name)), MAX_BASE_LENGTH)
    if len(base) >= BusinessPublicSlug.min_length:
        slug = BusinessPublicSlug(base)
        if not is_reserved_slug(slug):
            candidates.append(slug)

        candidates.extend(
            BusinessPublicSlug(f"{base}-{number}")
            for number in range(2, NUMBERED_VARIANTS + 2)
        )

    id_characters: str = str(business_id).rsplit("_", 1)[-1].replace("-", "")
    candidates.append(
        BusinessPublicSlug(
            f"{FALLBACK_PREFIX}-{id_characters[:FALLBACK_ID_CHARACTERS].lower()}"
        )
    )
    return candidates
