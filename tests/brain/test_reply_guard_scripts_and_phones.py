"""Invented values in scripts without spaces, Arabic and Indian grouping, and phones."""

import pytest

from tests.brain.reply_guard_helpers import unverified


@pytest.mark.parametrize(
    ("reply", "facts", "currency", "tag", "expected"),
    [
        ("ラーメンは9800円です", "Price: 1800 JPY", "JPY", "ja", ["9800"]),
        ("这道菜价格为999元", "Price: 120.00 CNY", "CNY", "zh", ["999元"]),
        ("這道菜要350元", "Price: 300 TWD", "TWD", "zh-Hant", ["350元"]),
        ("ข้าวผัดราคา90บาทค่ะ", "Price: 70.00 THB", "THB", "th", ["90"]),
        ("السعر بـ١٩ ريال", "Price: 15 SAR", "SAR", "ar", ["١٩ ريال"]),
        ("営業は22:30まで", "Hours 12:00-23:00", "JPY", "ja", ["22:30"]),
        ("ラーメンは1800円です", "Price: 1800 JPY", "JPY", "ja", []),
        ("这道菜价格为120元", "Price: 120.00 CNY", "CNY", "zh", []),
        ("ข้าวผัดราคา70บาทค่ะ", "Price: 70.00 THB", "THB", "th", []),
        ("السعر بـ١٥ ريال", "Price: 15 SAR", "SAR", "ar", []),
        ("営業は23:00まで", "Hours 12:00-23:00", "JPY", "ja", []),
    ],
)
def test_numbers_right_after_letters_of_scripts_without_spaces_are_checked(
    reply: str,
    facts: str,
    currency: str,
    tag: str,
    expected: list[str],
) -> None:
    assert unverified(reply, [facts], currency, tag) == expected


@pytest.mark.parametrize(
    ("reply", "facts", "currency"),
    [
        ("السعر ١٫٢٥٠ د.ك", "Price: 1.250 KWD", "KWD"),
        ("السعر ١٨٫٠٠ درهم", "Price: 18.00 AED", "AED"),
        ("السعر ١٬٥٠٠ ريال", "Price: 1500.00 SAR", "SAR"),
        ("قیمت ۱۸٫۰۰ درهم", "Price: 18.00 AED", "AED"),
    ],
)
def test_arabic_decimal_and_thousands_separators_are_read(
    reply: str,
    facts: str,
    currency: str,
) -> None:
    assert unverified(reply, [facts], currency, "ar", "fa") == []


def test_an_invented_arabic_decimal_amount_is_one_value() -> None:
    assert unverified("السعر ١٫٧٥٠ د.ك", ["Price: 1.250 KWD"], "KWD", "ar") == ["١٫٧٥٠"]


def test_lakh_and_crore_grouping_is_read_whole() -> None:
    hindi_price = '{"price_text":"₹1,00,000.00"}'

    for reply in ("It is ₹1,00,000 per night", "It is ₹100,000 per night"):
        assert unverified(reply, ["Price: 100000.00 INR"], "INR", "en") == []

    assert unverified("दाम ₹1,00,000 है", [hindi_price], "INR", "hi") == []
    assert unverified("It is ₹1,00,500", [hindi_price], "INR", "hi") == ["₹1,00,500"]
    assert unverified("It is ₹1,00,999.00", [hindi_price], "INR", "hi") == [
        "₹1,00,999.00"
    ]
    assert unverified("It is Rs. 1,00,750", [hindi_price], "INR", "hi") != []
    assert unverified("দাম 1,00,000.00৳", ["Price: 100000.00 BDT"], "BDT", "bn") == []
    assert unverified("Rs 1,00,000", ["Price: 100000.00 PKR"], "PKR", "ur") == []


@pytest.mark.parametrize(
    ("reply", "public_phone", "currency"),
    [
        ("Call us at 2222 3333", "+965 2222 3333", "KWD"),
        ("Call us at 22223333", "+965 2222 3333", "KWD"),
        ("Call us at 6123 4567", "+65 6123 4567", "SGD"),
        ("Call us at 2123 4567", "+852 2123 4567", "HKD"),
        ("Call us at 03-123-4567", "+972 3-123-4567", "ILS"),
        ("Call us at 02 123 45 67", "+32 2 123 45 67", "EUR"),
        ("Call us at 09 301 2345", "+64 9 301 2345", "NZD"),
        ("Call us at 030 1234567", "+49 30 1234567", "EUR"),
        ("Call us at 032 212 34 56", "+995 32 212 34 56", "GEL"),
    ],
)
def test_national_forms_of_a_public_phone_are_supported(
    reply: str,
    public_phone: str,
    currency: str,
) -> None:
    assert (
        unverified(reply, [f"Public phone number: {public_phone}"], currency, "en")
        == []
    )


def test_a_phone_the_customer_typed_nationally_may_be_repeated_internationally() -> (
    None
):
    assert (
        unverified(
            "We will call you at +965 9876 5432.",
            [],
            "KWD",
            "en",
            customer=["My number is 9876 5432"],
        )
        == []
    )
    assert unverified(
        "Call us at 2222 4444", ["Public phone number: +965 2222 3333"], "KWD", "en"
    ) == ["2222 4444"]
