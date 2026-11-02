"""Card, security code, IBAN and ID numbers masked; everything else kept."""

import pytest

from app.utilities.privacy.sensitive_number_checks import (
    is_card_number,
    is_iban,
    is_italian_tax_code,
    passes_luhn,
)
from app.utilities.privacy.sensitive_numbers import (
    ACCOUNT_PLACEHOLDER,
    CARD_PLACEHOLDER,
    ID_NUMBER_PLACEHOLDER,
    SECURITY_CODE_PLACEHOLDER,
    holds_card_number,
    mask_sensitive_numbers,
)

NBSP: str = chr(0xA0)


def test_the_payment_test_message_is_masked() -> None:
    assert (
        mask_sensitive_numbers("4242 4242 4242 4242 cvv 123")
        == f"{CARD_PLACEHOLDER} cvv {SECURITY_CODE_PLACEHOLDER}"
    )


@pytest.mark.parametrize(
    "written",
    [
        "4242424242424242",
        "4242 4242 4242 4242",
        "4242-4242-4242-4242",
        NBSP.join(["4242"] * 4),
        "4 2 4 2 4 2 4 2 4 2 4 2 4 2 4 2",
        "5555 5555 5555 4444",
        "3782 822463 10005",
        "6011 1111 1111 1117",
        "4111111111111111",
    ],
)
def test_luhn_valid_cards_are_masked_however_written(written: str) -> None:
    assert mask_sensitive_numbers(f"my card is {written}, thanks") == (
        f"my card is {CARD_PLACEHOLDER}, thanks"
    )


def test_the_expiry_and_code_said_after_the_card_go_with_it() -> None:
    assert mask_sensitive_numbers("4242 4242 4242 4242 12 27 123") == CARD_PLACEHOLDER
    assert mask_sensitive_numbers("4242 4242 4242 4242 123 ok") == (
        f"{CARD_PLACEHOLDER} ok"
    )


@pytest.mark.parametrize(
    ("said", "kept"),
    [
        ("cvv 123", "cvv "),
        ("CVC: 1234", "CVC: "),
        ("cvv123", "cvv"),
        ("il cvv è 321", "il cvv è "),
        ("il codice di sicurezza 321", "il codice di sicurezza "),
        ("the security code is 987", "the security code is "),
    ],
)
def test_a_named_security_code_is_masked(said: str, kept: str) -> None:
    assert mask_sensitive_numbers(said) == kept + SECURITY_CODE_PLACEHOLDER


@pytest.mark.parametrize(
    "iban",
    [
        "IT60 X054 2811 1010 0000 0123 456",
        "IT60X0542811101000000123456",
        "it60x0542811101000000123456",
        "DE89 3704 0044 0532 0130 00",
        "GE29NB0000000101904917",
    ],
)
def test_an_iban_is_masked(iban: str) -> None:
    assert mask_sensitive_numbers(f"IBAN: {iban} grazie") == (
        f"IBAN: {ACCOUNT_PLACEHOLDER} grazie"
    )


def test_an_italian_tax_code_and_a_named_document_are_masked() -> None:
    assert mask_sensitive_numbers("codice fiscale RSSMRA85T10A562S") == (
        f"codice fiscale {ID_NUMBER_PLACEHOLDER}"
    )
    assert mask_sensitive_numbers("passaporto YA1234567 per favore") == (
        f"passaporto {ID_NUMBER_PLACEHOLDER} per favore"
    )
    assert mask_sensitive_numbers("my passport number is AB1234567") == (
        f"my passport number is {ID_NUMBER_PLACEHOLDER}"
    )


@pytest.mark.parametrize(
    "text",
    [
        "Call me on +39 333 123 4567 or 0039 333 1234567.",
        "+44 7911 123456",
        "A table for 4 people on 25.10.2026 at 19:30, ref BK-4821.",
        "The total is 1 500 000 000 000 som.",
        "Order 4242424242424241 (not a card: the Luhn check fails).",
        "It took 0.30000000000000004 s at 1730000000000 ms.",
        "ok20 people tonight please",
        "RSSMRA85T10A562X is not a tax code: its check letter is wrong.",
        "documento di trasporto 2026",
        "The cvv? I will pay on the link.",
    ],
)
def test_other_numbers_stay(text: str) -> None:
    assert mask_sensitive_numbers(text) == text


def test_masking_twice_changes_nothing() -> None:
    once: str = mask_sensitive_numbers(
        "Il mio numero di carta è 5555 5555 5555 4444 e il codice di sicurezza 321"
    )

    assert once == (
        f"Il mio numero di carta è {CARD_PLACEHOLDER} e il codice di sicurezza "
        f"{SECURITY_CODE_PLACEHOLDER}"
    )
    assert mask_sensitive_numbers(once) == once


def test_the_checks() -> None:
    assert passes_luhn("79927398713") and not passes_luhn("79927398710")
    assert is_card_number("4242424242424242")
    assert not is_card_number("0242424242424242")
    assert not is_card_number("424242424242")
    assert is_iban("GB82 WEST 1234 5698 7654 32")
    assert not is_iban("GB82 WEST 1234 5698 7654 33")
    assert not is_iban("ZZ82WEST12345698765432")
    assert is_italian_tax_code("RSSMRA80A01H501U")
    assert not is_italian_tax_code("RSSMRA80A01H501")


def test_a_run_grouped_in_thousands_is_an_amount() -> None:
    assert not holds_card_number(["4", "242", "424", "242", "424", "242"])
    assert holds_card_number(["4242", "4242", "4242", "4242"])
