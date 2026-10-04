"""The context line naming the customer's language for the model."""

from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    ScriptCode,
)
from app.utilities.conversations.reply_language import (
    describe_reply_language,
    describe_script,
)


def test_the_line_names_the_language_and_its_tag() -> None:
    assert describe_reply_language(LanguageTag("he"), None) == (
        "Reply language: Hebrew (he)."
    )
    assert describe_reply_language(LanguageTag("pt-BR"), None) == (
        "Reply language: Portuguese (Brazil) (pt-BR)."
    )


def test_a_transliteration_asks_for_the_language_own_script() -> None:
    assert describe_reply_language(LanguageTag("ru"), ScriptCode("Latn")) == (
        "Reply language: Russian (ru). The customer types it in Latin letters; "
        "reply in Cyrillic script unless they ask for Latin letters."
    )


def test_an_unknown_script_is_named_by_its_code() -> None:
    assert describe_script("Qaaa") == "Qaaa"
