"""Variables in braces: found, checked, filled; variants chosen by language."""

from app.schemas.constants.inbox import QuickReplyVariable
from app.schemas.domain.quick_replies import QuickReplyVariant
from app.schemas.typings.inbox.constrained_strings import QuickReplyTemplateText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.inbox.quick_reply_templates import (
    choose_variant,
    fill_variables,
    unknown_placeholders,
    variables_in,
)


def variant(language: str) -> QuickReplyVariant:
    return QuickReplyVariant(
        language=LanguageTag(language), text=QuickReplyTemplateText(language)
    )


def test_variables_are_found_once_in_order_and_strangers_reported() -> None:
    texts = ["{name}, your table {booking_time}", "{name} {table_number} { } {"]

    assert variables_in(texts) == [
        QuickReplyVariable.NAME,
        QuickReplyVariable.BOOKING_TIME,
    ]
    assert unknown_placeholders(texts) == ["table_number"]


def test_filling_keeps_other_braces_and_lists_what_is_missing() -> None:
    text, missing = fill_variables(
        "{name}: {booking_time} {booking_time} {other} {}",
        {QuickReplyVariable.NAME: "Nino"},
    )

    assert text == "Nino: {booking_time} {booking_time} {other} {}"
    assert missing == [QuickReplyVariable.BOOKING_TIME]


def test_the_variant_follows_the_language_then_the_fallback_then_the_first() -> None:
    variants = [variant("en"), variant("pt-BR"), variant("ka")]

    def chosen(language: str | None, fallback: str = "ka") -> str:
        return str(
            choose_variant(
                variants,
                None if language is None else LanguageTag(language),
                LanguageTag(fallback),
            ).language
        )

    assert chosen("pt-BR") == "pt-BR"
    assert chosen("pt") == "pt-BR"
    assert chosen("de") == "ka"
    assert chosen(None) == "ka"
    assert chosen("de", fallback="ru") == "en"
