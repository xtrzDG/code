import pytest

from app.schemas.constants.businesses import Weekday
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.dto.knowledge_admin import KnowledgeItemPatch
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.utilities.knowledge.localized_texts import (
    build_localized_rule_lines,
    split_rule_lines,
)
from app.utilities.knowledge.money_formatting import (
    format_money_minor,
    resolve_babel_locale,
)
from app.utilities.knowledge.opening_hours import (
    format_minute,
    validate_opening_intervals,
)
from app.utilities.knowledge.request_parsing import (
    canonical_language_tag,
    json_body_openapi,
    negotiate_language,
    parse_boolean_text,
    parse_json_body,
    parse_language_parameter,
    parse_path_value,
    parse_query_value,
)

NBSP: str = "\xa0"
RLM: str = "‏"


def interval(weekday: Weekday, opens: int, closes: int) -> OpeningInterval:
    return OpeningInterval(
        weekday=weekday,
        opens_at=OpeningMinuteOfDay(opens),
        closes_at=ClosingMinuteOfDay(closes),
    )


@pytest.mark.parametrize(
    ("amount_minor", "currency", "language", "expected"),
    [
        (1800, "GEL", "ka", f"18,00{NBSP}₾"),
        (1800, "GEL", "en", "GEL18.00"),
        (1250, "EUR", "de", f"12,50{NBSP}€"),
        (1250, "EUR", "fr-FR", f"12,50{NBSP}€"),
        (1500, "JPY", "ja", "￥1,500"),
        (1500, "JPY", "en", "¥1,500"),
        (12500, "KWD", "en", "KWD12.500"),
        (12345, "ILS", "he", f"{RLM}123.45{NBSP}{RLM}₪"),
        (100, "BRL", "pt-BR", f"R${NBSP}1,00"),
        (100, "USD", "xx", "$1.00"),
    ],
)
def test_money_is_formatted_with_currency_digits_and_locale(
    amount_minor: int,
    currency: str,
    language: str,
    expected: str,
) -> None:
    formatted = format_money_minor(
        MoneyAmountMinor(amount_minor),
        CurrencyCode(currency),
        LanguageTag(language),
    )

    assert formatted == expected


def test_arabic_prices_keep_latin_digits_for_the_numbers_guard() -> None:
    formatted = format_money_minor(
        MoneyAmountMinor(2500),
        CurrencyCode("AED"),
        LanguageTag("ar"),
    )

    assert "25.00" in formatted


def test_unknown_locales_fall_back_to_base_language_then_english() -> None:
    assert str(resolve_babel_locale(LanguageTag("ka-GE"))) == "ka_GE"
    assert str(resolve_babel_locale(LanguageTag("xx-YY"))) == "en"


def test_opening_hours_are_sorted_and_allow_midnight_and_overnight_split() -> None:
    hours = validate_opening_intervals(
        [
            interval(Weekday.SATURDAY, 0, 120),
            interval(Weekday.FRIDAY, 1080, 1440),
            interval(Weekday.MONDAY, 900, 1380),
            interval(Weekday.MONDAY, 540, 840),
            interval(Weekday.TUESDAY, 540, 720),
            interval(Weekday.TUESDAY, 720, 1260),
        ],
        subject="Opening hours",
    )

    assert [(hour.weekday, hour.opens_at) for hour in hours] == [
        (Weekday.MONDAY, 540),
        (Weekday.MONDAY, 900),
        (Weekday.TUESDAY, 540),
        (Weekday.TUESDAY, 720),
        (Weekday.FRIDAY, 1080),
        (Weekday.SATURDAY, 0),
    ]


def test_opening_interval_must_close_after_it_opens() -> None:
    with pytest.raises(ValidationFailedError, match="two days"):
        validate_opening_intervals(
            [interval(Weekday.FRIDAY, 1320, 120)],
            subject="Opening hours",
        )

    with pytest.raises(ValidationFailedError, match="closes before it opens"):
        validate_opening_intervals(
            [interval(Weekday.FRIDAY, 600, 600)],
            subject="Opening hours",
        )


def test_overlapping_intervals_of_one_day_are_rejected() -> None:
    with pytest.raises(ValidationFailedError, match="overlap"):
        validate_opening_intervals(
            [
                interval(Weekday.SUNDAY, 600, 900),
                interval(Weekday.SUNDAY, 840, 1200),
            ],
            subject="Opening hours",
        )

    with pytest.raises(ValidationFailedError, match="more than"):
        validate_opening_intervals(
            [
                interval(Weekday.SUNDAY, start, start + 10)
                for start in range(0, 130, 10)
            ],
            subject="Opening hours",
        )


def test_minutes_render_as_clock_time() -> None:
    assert format_minute(0) == "00:00"
    assert format_minute(570) == "09:30"
    assert format_minute(1440) == "24:00"


def test_rule_lines_round_trip_and_require_equal_counts() -> None:
    text = build_localized_rule_lines(en=["A", "B"], ru=["А", "Б"], ka=["ა", "ბ"])

    assert split_rule_lines(text.values[LanguageTag("ru")]) == ["А", "Б"]
    with pytest.raises(ValueError, match="same number"):
        build_localized_rule_lines(en=["A"], ru=["А", "Б"])


def test_json_bodies_are_validated_in_json_mode() -> None:
    patch = parse_json_body(KnowledgeItemPatch, b'{"kind": "faq", "body": null}')

    assert patch.kind == "faq"
    assert patch.model_fields_set == {"kind", "body"}
    with pytest.raises(ValidationFailedError, match="kind"):
        parse_json_body(KnowledgeItemPatch, b'{"kind": "spaceship"}')
    with pytest.raises(ValidationFailedError, match="JSON object"):
        parse_json_body(KnowledgeItemPatch, b"  ")
    with pytest.raises(ValidationFailedError):
        parse_json_body(KnowledgeItemPatch, b"{not json")


def test_path_and_query_values_become_typed_or_application_errors() -> None:
    business_id = BusinessId()

    assert parse_path_value(BusinessId, str(business_id), "Business") == business_id
    with pytest.raises(NotFoundError):
        parse_path_value(BusinessId, "not-an-id", "Business")

    assert parse_query_value(parse_boolean_text, "TRUE", "is_active") is True
    assert parse_query_value(parse_boolean_text, "no", "is_active") is False
    assert parse_query_value(parse_boolean_text, " ", "is_active") is None
    with pytest.raises(ValidationFailedError, match="is_active"):
        parse_query_value(parse_boolean_text, "maybe", "is_active")


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


def test_language_parameter_and_accept_language_negotiation() -> None:
    assert parse_language_parameter("he") == "he"
    assert parse_language_parameter(None) is None
    with pytest.raises(ValidationFailedError, match="language"):
        parse_language_parameter("123")

    assert negotiate_language("ru-RU,ru;q=0.9,en;q=0.8") == "ru-RU"
    assert negotiate_language("en;q=0.5, ka;q=0.9, *;q=0.1") == "ka"
    assert negotiate_language("ar;q=0") is None
    assert negotiate_language("de;q=abc, he") == "he"
    assert negotiate_language(None) is None


def test_openapi_body_schema_has_an_id_and_one_of_for_several_models() -> None:
    single = json_body_openapi(KnowledgeItemPatch)
    schema = single["requestBody"]["content"]["application/json"]["schema"]

    assert schema["$id"].endswith("KnowledgeItemPatch")
    several = json_body_openapi(KnowledgeItemPatch, KnowledgeItemPatch)
    assert "oneOf" in several["requestBody"]["content"]["application/json"]["schema"]
