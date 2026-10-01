from decimal import Decimal

import pytest

from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.utilities.reply_guard.invented_numbers import find_unverified_values
from app.utilities.reply_guard.lexicons import build_guard_lexicon
from app.utilities.reply_guard.number_mentions import (
    NumberMention,
    extract_number_mentions,
)
from app.utilities.reply_guard.numerals import (
    normalize_digits,
    parse_amount_candidates,
)


def languages(*tags: str) -> list[LanguageTag]:
    return [LanguageTag(tag) for tag in tags]


def mentions(text: str, currency: str, *tags: str) -> list[NumberMention]:
    lexicon = build_guard_lexicon(languages(*tags), [CurrencyCode(currency)])
    return extract_number_mentions(text, lexicon)


def unverified(
    reply: str,
    evidence: list[str],
    currency: str,
    *tags: str,
) -> list[str]:
    return [
        str(value)
        for value in find_unverified_values(
            MessageText(reply),
            evidence,
            languages(*tags),
            [CurrencyCode(currency)],
        )
    ]


@pytest.mark.parametrize(
    ("token", "values"),
    [
        ("18", {"18"}),
        ("18.50", {"18.5"}),
        ("18,50", {"18.5"}),
        ("1,500", {"1500", "1.5"}),
        ("1.500", {"1500", "1.5"}),
        ("1 500", {"1500"}),
        ("1 500", {"1500"}),
        ("1,500.50", {"1500.5"}),
        ("1.500,50", {"1500.5"}),
        ("1.500.000", {"1500000"}),
        ("1'500", {"1500"}),
    ],
)
def test_numbers_are_read_in_every_locale_convention(
    token: str,
    values: set[str],
) -> None:
    assert parse_amount_candidates(token) == {Decimal(value) for value in values}


def test_digits_of_every_numbering_system_are_normalized() -> None:
    assert normalize_digits("٤٥ ريال، ۱۲:۳۰، १२३, ４５") == "45 ريال، 12:30، 123, 45"


@pytest.mark.parametrize(
    ("text", "currency", "tags", "expected"),
    [
        ("Хачапури — 18 лари", "GEL", ("ru",), "18 лари"),
        ("ხაჭაპური 18 ლარი ღირს", "GEL", ("ka",), "18 ლარი"),
        ("Khachapuri: 18 GEL", "GEL", ("en",), "18 GEL"),
        ("Khachapuri: ₾18", "GEL", ("en",), "₾18"),
        ("Breakfast €12.50", "EUR", ("en",), "€12.50"),
        ("Brunch $25", "USD", ("en",), "$25"),
        ("המנה עולה 45 ₪", "ILS", ("he",), "45 ₪"),
        ("המנה עולה 45 שקלים", "ILS", ("he",), "45 שקלים"),
        ("السعر 45 ₪", "ILS", ("ar",), "45 ₪"),
        ("Խորոված՝ 4500 ֏", "AMD", ("hy",), "4500 ֏"),
        ("Խորոված՝ 4500 դրամ", "AMD", ("hy",), "4500 դրամ"),
        ("Бешбармак — 3500 ₸", "KZT", ("kk", "ru"), "3500 ₸"),
        ("Бешбармак — 3500 тенге", "KZT", ("ru",), "3500 тенге"),
        ("Pierogi 32 zł", "PLN", ("pl",), "32 zł"),
        ("Pierogi 32 złote", "PLN", ("pl",), "32 złote"),
        ("Kebap 250 ₺", "TRY", ("tr",), "250 ₺"),
        ("Ramen ¥1,200", "JPY", ("ja",), "¥1,200"),
        ("Plov 12 ₼", "AZN", ("az",), "12 ₼"),
    ],
)
def test_money_is_recognized_in_any_currency(
    text: str,
    currency: str,
    tags: tuple[str, ...],
    expected: str,
) -> None:
    money = [mention for mention in mentions(text, currency, *tags) if mention.is_money]

    assert [mention.text for mention in money] == [expected]


@pytest.mark.parametrize(
    ("text", "tags", "time"),
    [
        ("Ждём вас в 19:30", ("ru",), (19, 30)),
        ("See you at 7:30 pm", ("en",), (19, 30)),
        ("See you at 7 PM", ("en",), (19, 0)),
        ("Open until 11 p.m.", ("en",), (23, 0)),
        ("Rendez-vous à 19h30", ("fr",), (19, 30)),
        ("بانتظارك الساعة ١٩:٣٠", ("ar",), (19, 30)),
        ("19:30-ზე გელოდებით", ("ka",), (19, 30)),
        ("12:00 AM", ("en",), (0, 0)),
    ],
)
def test_times_are_recognized(
    text: str,
    tags: tuple[str, ...],
    time: tuple[int, int],
) -> None:
    times = {time for mention in mentions(text, "EUR", *tags) for time in mention.times}

    assert times == {time}


@pytest.mark.parametrize(
    ("text", "tags", "date"),
    [
        ("Бронь на 5 октября", ("ru",), (None, 10, 5)),
        ("Бронь на 5-го октября", ("ru",), (None, 10, 5)),
        ("ჯავშანი 5 ოქტომბერს", ("ka",), (None, 10, 5)),
        ("Ամրագրումը հոկտեմբերի 5-ին", ("hy",), (None, 10, 5)),
        ("Booked for October 5, 2026", ("en",), (2026, 10, 5)),
        ("Booked for the 5th of October", ("en",), (None, 10, 5)),
        ("Reserva para el 5 de octubre", ("es",), (None, 10, 5)),
        ("Reservierung am 5. Oktober", ("de",), (None, 10, 5)),
        ("Rezerwacja 5 października", ("pl",), (None, 10, 5)),
        ("Rezervasyon 5 Ekim", ("tr",), (None, 10, 5)),
        ("预订10月5日", ("zh",), (None, 10, 5)),
        ("2026年10月5日に予約", ("ja",), (2026, 10, 5)),
        ("Booking 2026-10-05", ("en",), (2026, 10, 5)),
    ],
)
def test_dates_are_recognized_with_month_names_in_many_languages(
    text: str,
    tags: tuple[str, ...],
    date: tuple[int | None, int, int],
) -> None:
    dates = {date for mention in mentions(text, "EUR", *tags) for date in mention.dates}

    assert date in dates


def test_numeric_dates_keep_both_day_month_orders_and_24_7_is_not_a_date() -> None:
    found = mentions("05.10.2026, 5/10 and open 24/7", "EUR", "en")

    assert found[0].dates == {(2026, 10, 5), (2026, 5, 10)}
    assert found[1].dates == {(None, 10, 5), (None, 5, 10)}
    assert all(not mention.dates for mention in found[2:])


def test_phone_numbers_are_one_mention() -> None:
    found = mentions("Call +995 555 12 34 56 or 555-12-34-56", "GEL", "en")

    assert [mention.phone_digits for mention in found] == ["995555123456", "555123456"]


def test_identifiers_inside_words_are_ignored() -> None:
    found = mentions("Room B12, code A4 and booking_7f3e", "EUR", "en")

    assert found == []


EVIDENCE: list[str] = [
    "Business: Sakhli. Local time at the business: Thursday 2026-10-01 14:05 "
    "(Asia/Tbilisi). Next days: Fri 2026-10-02, Sat 2026-10-03, Sun 2026-10-04, "
    "Mon 2026-10-05. Customer phone: +995555123456.",
    "Hours: Mon-Sun 12:00-23:00",
    "Adjarian khachapuri: 18 GEL",
    '{"items":[{"title":"Khinkali","price":"1.20","currency":"GEL"}]}',
    '{"slots":[{"date":"2026-10-05","time":"19:30","resource_name":"Table 4"}]}',
    "Хочу столик на 6 человек в 7 вечера",
]


@pytest.mark.parametrize(
    ("reply", "tags"),
    [
        ("Аджарский хачапури стоит 18 лари, хинкали — 1,20 ₾.", ("ru",)),
        ("აჭარული ხაჭაპური 18 ლარი ღირს, 5 ოქტომბერს 19:30-ზე გელოდებით.", ("ka",)),
        ("Khachapuri is ₾18 (GEL 18.00); we are open 12:00–23:00.", ("en",)),
        ("A table for 6 on October 5 at 7:30 pm is free.", ("en",)),
        ("Столик на 6 человек 5 октября в 19:00 свободен.", ("ru",)),
        ("We will call you at +995 555 12 34 56.", ("en",)),
        ("Мы перезвоним на 555 12 34 56.", ("ru",)),
        ("Tomorrow, 2026-10-02, we open at 12:00.", ("en",)),
        ("We have 2 halls and 3 terraces.", ("en",)),
        ("Sakhli works 7 days a week.", ("en",)),
    ],
)
def test_supported_replies_pass(reply: str, tags: tuple[str, ...]) -> None:
    assert unverified(reply, EVIDENCE, "GEL", *tags) == []


@pytest.mark.parametrize(
    ("reply", "tags", "expected"),
    [
        ("Хачапури стоит 20 лари.", ("ru",), ["20 лари"]),
        ("ხაჭაპური 25 ლარი ღირს.", ("ka",), ["25 ლარი"]),
        ("Khachapuri costs 5 GEL today.", ("en",), ["5 GEL"]),
        ("We give a 15% discount.", ("en",), ["15%"]),
        ("We give a 5% discount.", ("en",), ["5%"]),
        ("The kitchen closes at 22:30.", ("en",), ["22:30"]),
        ("Come on 7 October.", ("en",), ["7 October"]),
        ("ჯავშანი 9 ოქტომბერს.", ("ka",), ["9 ოქტომბერს"]),
        ("Call us at +995 599 00 00 00.", ("en",), ["+995 599 00 00 00"]),
        ("Deposit 50 ₾ and 2 hours later 30 €.", ("en",), ["50 ₾", "30 €"]),
        ("המחיר 45 ₪", ("he",), ["45 ₪"]),
        ("السعر ٤٥ ₪", ("ar",), ["٤٥ ₪"]),
        ("Գինը 4500 ֏ է", ("hy",), ["4500 ֏"]),
        ("Стоимость 3500 ₸", ("ru",), ["3500 ₸"]),
        ("Price $40 and again $40.", ("en",), ["$40"]),
    ],
)
def test_invented_values_are_reported_as_written(
    reply: str,
    tags: tuple[str, ...],
    expected: list[str],
) -> None:
    assert unverified(reply, EVIDENCE, "GEL", *tags) == expected


def test_full_hours_are_supported_by_the_hour_the_customer_named() -> None:
    assert unverified("See you at 19:00", ["at 7 please"], "EUR", "en") == []
    assert unverified("See you at 7 pm", ["at 7 please"], "EUR", "en") == []
    assert unverified("See you at 19:15", ["at 7 please"], "EUR", "en") == ["19:15"]


def test_thousands_separators_of_any_locale_match_the_evidence() -> None:
    evidence = ['{"price":"1500.00","currency":"AMD"}']

    for reply in ("1 500 ֏", "1,500 AMD", "1.500 դրամ", "1500.00 ֏"):
        assert unverified(reply, evidence, "AMD", "hy", "ru") == []


def test_evidence_in_other_numbering_systems_is_understood() -> None:
    assert unverified("السعر 45 ₪", ["السعر ٤٥ ₪"], "ILS", "ar") == []
    assert unverified("Price 45 ₪", ["المجموع ٤٥"], "ILS", "ar", "en") == []
