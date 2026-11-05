"""
The sentence of the call greeting that names the business's other
languages (CALL_LANGUAGE_OFFER), filled for one greeting language.

The other languages are named in the greeting's language by CLDR (Babel:
"georgiano", "russo") and listed the way that language lists things
("georgiano, russo e inglese"); a language CLDR cannot name in it is
named in English. The sentence is left out when the greeting's language
has no offer text (it would otherwise be English inside a Korean
greeting) and when the business speaks no other language.
"""

from babel import Locale, UnknownLocaleError
from babel.lists import format_list

from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import LanguageDisplayName
from app.utilities.conversations.assistant_texts.call_language_texts import (
    CALL_LANGUAGE_OFFER,
    LANGUAGES_PLACEHOLDER,
)
from app.utilities.localization.cldr_language_names import get_english_locale
from app.utilities.localization.display_names import build_language_display_name
from app.utilities.localization.language_tags import base_language_code

ENGLISH_LANGUAGE_CODE: str = "en"


def other_languages(
    spoken: list[LanguageTag], greeting_language: LanguageTag
) -> list[LanguageTag]:
    """The business's languages besides the greeting's, one per base language."""

    greeting_base: str = base_language_code(greeting_language)
    found: dict[str, LanguageTag] = {}
    for language in spoken:
        base: str = base_language_code(language)
        if base != greeting_base and base not in found:
            found[base] = language
    return list(found.values())


def language_offer_sentence(
    greeting_language: LanguageTag, others: list[LanguageTag]
) -> str | None:
    """
    CALL_LANGUAGE_OFFER in the greeting's language, naming `others`; None
    when the sentence is not said.
    """

    base: str = base_language_code(greeting_language)
    template: str | None = offer_template(greeting_language, base)
    if template is None or others == []:
        return None

    locale: Locale = display_locale(base)
    names: list[str] = [str(language_name(language, locale)) for language in others]
    return template.replace(LANGUAGES_PLACEHOLDER, format_list(names, locale=locale))


def offer_template(greeting_language: LanguageTag, base: str) -> str | None:
    """The offer written in the greeting's language (exact tag or base), else None."""

    exact: object = CALL_LANGUAGE_OFFER.values.get(greeting_language)
    if exact is not None:
        return str(exact)
    by_base: object = CALL_LANGUAGE_OFFER.values.get(LanguageTag(base))
    return None if by_base is None else str(by_base)


def display_locale(base: str) -> Locale:
    """The CLDR locale of a base language; English for one CLDR lacks."""

    try:
        return Locale.parse(base)
    except UnknownLocaleError, ValueError:
        return get_english_locale()


def language_name(language: LanguageTag, locale: Locale) -> LanguageDisplayName:
    """A language named in the locale, else in English, else by its tag."""

    named: LanguageDisplayName | None = build_language_display_name(language, locale)
    if named is not None:
        return named
    english: LanguageDisplayName | None = build_language_display_name(
        language, get_english_locale()
    )
    return english if english is not None else LanguageDisplayName(str(language))
