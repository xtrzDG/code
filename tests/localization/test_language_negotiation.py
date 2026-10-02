"""`?language=`, Accept-Language and optional query flags at the HTTP boundary."""

import pytest

from app.gateways.http.language_negotiation import (
    canonical_language_tag,
    negotiate_language,
    parse_language_parameter,
    parse_quality,
)
from app.gateways.http.query_parsing import parse_boolean_text, parse_optional
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.exceptions.application_errors import ValidationFailedError


@pytest.mark.parametrize(
    ("raw_tag", "expected"),
    [
        ("pt-br", "pt-BR"),
        ("ZH_hant", "zh-Hant"),
        ("sr-latn-rs", "sr-Latn-RS"),
        ("ka", "ka"),
        ("1234", None),
    ],
)
def test_language_tags_are_normalized(raw_tag: str, expected: str | None) -> None:
    assert canonical_language_tag(raw_tag) == expected


def test_language_parameter_is_typed_or_rejected_without_echo() -> None:
    assert parse_language_parameter("he") == "he"
    assert parse_language_parameter(" pt-br ") == "pt-BR"
    assert parse_language_parameter(None) is None
    assert parse_language_parameter("  ") is None
    with pytest.raises(ValidationFailedError, match="language") as raised:
        parse_language_parameter("123")

    assert "123" not in str(raised.value)


def test_accept_language_picks_the_best_valid_language() -> None:
    assert negotiate_language("ru-RU,ru;q=0.9,en;q=0.8") == "ru-RU"
    assert negotiate_language("en;q=0.5, ka;q=0.9, *;q=0.1") == "ka"
    assert negotiate_language("ar;q=0") is None
    assert negotiate_language("de;q=abc, he") == "he"
    assert negotiate_language("de, en") == "de"
    assert negotiate_language(None) is None


def test_quality_weights_default_to_one_and_malformed_to_zero() -> None:
    assert parse_quality(None) == 1.0
    assert parse_quality("0.4") == 0.4
    assert parse_quality("1.2.3") == 0.0


def test_optional_query_values_are_typed_blank_is_absent() -> None:
    assert parse_optional("TRUE", parse_boolean_text, "is_active") is True
    assert parse_optional("no", parse_boolean_text, "is_active") is False
    assert parse_optional("0", parse_boolean_text, "is_active") is False
    assert parse_optional(" ", parse_boolean_text, "is_active") is None
    assert parse_optional(None, parse_boolean_text, "is_active") is None
    assert parse_optional("faq", KnowledgeItemKind, "kind") == KnowledgeItemKind.FAQ
    with pytest.raises(ValidationFailedError, match="is_active"):
        parse_optional("maybe", parse_boolean_text, "is_active")
    with pytest.raises(ValidationFailedError, match="kind"):
        parse_optional("spaceship", KnowledgeItemKind, "kind")


def test_accept_language_items_with_odd_spacing_and_parameters() -> None:
    assert negotiate_language("  en-GB  ;  q = 0.4 ,  ka ; q=0.9 ") == "ka"
    assert negotiate_language("de;level=1, fr") == "fr"
    assert negotiate_language("de;q=, fr") == "fr"
    assert negotiate_language("de;q=0.5;x=1") is None


def test_long_accept_language_headers_are_cut_quickly() -> None:
    # The header is cut at 1024 characters: the first item survives without
    # its weight, and no pattern ever scans the run of spaces.
    hostile: str = "en" + " " * 50_000 + ";q=0.9"
    assert negotiate_language(hostile) == "en"
    many_items: str = ",".join(["xx-YY;q=0.1"] * 5_000)
    assert negotiate_language(many_items + ",ka") == "xx-YY"
