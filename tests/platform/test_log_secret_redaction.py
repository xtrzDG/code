"""
Log lines and error reports never carry a credential, a card number, a
security code or an IBAN: the formatters redact the message and the
traceback, and Sentry's scrubbing does the same (LOG-02).
"""

import logging
import sys

import pytest
from sentry_sdk.types import Event

from app.facilitators.observability.sentry_event_scrubbing import (
    mask_personal_data,
    scrub_event,
)
from app.utilities.observability.log_formatting import (
    JsonLogFormatter,
    TextLogFormatter,
    redact_log_text,
    redact_secrets,
)

CARD_MESSAGE: str = "4242 4242 4242 4242 cvv 123"
STRIPE_KEY: str = "sk_live_" + "51H8xYzAbCdEfGhIjKlMnOp"


@pytest.mark.parametrize(
    ("text", "redacted"),
    [
        (
            "Authorization: Bearer header.payload.signature",
            "Authorization: Bearer <redacted>",
        ),
        ("authorization=basic dXNlcjpwYXNzd29yZA==", "authorization=basic <redacted>"),
        (f"Stripe refused {STRIPE_KEY}", "Stripe refused <redacted>"),
        ("key rk_test_" + "4eC39HqLyjWDarjtT1zdp7dc", "key <redacted>"),
        ("secret whsec_" + "MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw", "secret <redacted>"),
        (
            "public API key awk_mzxw6ytb_" + "Q3m8sLkP0aZ7dJ2nB5vC9xR1tY4uW6eH",
            "public API key awk_mzxw6ytb_<redacted>",
        ),
    ],
)
def test_credentials_are_redacted(text: str, redacted: str) -> None:
    assert redact_secrets(text) == redacted


@pytest.mark.parametrize(
    "text",
    [
        "Bearer token missing",
        "awk_mzxw6ytb refused: revoked",
        "Stripe returned 402 for invoice in_1Pq",
    ],
)
def test_words_and_public_prefixes_stay(text: str) -> None:
    assert redact_secrets(text) == text


def test_a_log_text_loses_cards_accounts_and_contacts() -> None:
    assert redact_log_text(
        f"{CARD_MESSAGE} from +39 333 123 4567, IBAN IT60X0542811101000000123456"
    ) == ("[card number] cvv [security code] from [phone], IBAN [account number]")


def record_with_error(message: str, *args: object) -> logging.LogRecord:
    try:
        raise ValueError(f"declined card {CARD_MESSAGE} of mario@example.it")
    except ValueError:
        return logging.LogRecord(
            "app.payments", logging.ERROR, __file__, 1, message, args, sys.exc_info()
        )


def test_json_lines_redact_the_message_and_the_traceback() -> None:
    record = record_with_error("Retry with %s and %s", STRIPE_KEY, CARD_MESSAGE)

    line: str = JsonLogFormatter().format(record)

    for leaked in ("4242", "cvv 123", "sk_live_", "mario@example.it"):
        assert leaked not in line
    assert "[card number] cvv [security code]" in line
    assert "ValueError: declined card [card number]" in line


def test_text_lines_redact_the_message_and_the_traceback() -> None:
    record = record_with_error("Webhook Authorization: Bearer abcdefghijklmnop")

    line: str = TextLogFormatter().format(record)

    assert "abcdefghijklmnop" not in line and "4242" not in line
    assert "Bearer <redacted>" in line


def test_sentry_reports_lose_cards_and_security_codes() -> None:
    event: Event = {
        "message": f"Payment failed for {CARD_MESSAGE}",
        "exception": {
            "values": [{"type": "ValueError", "value": f"card {CARD_MESSAGE}"}]
        },
        "logentry": {"message": "Bearer abcdefghijklmnop", "formatted": CARD_MESSAGE},
    }

    scrubbed = scrub_event(event, {})

    assert scrubbed is not None
    text: str = str(scrubbed)
    assert "4242" not in text and "123" not in text
    assert "abcdefghijklmnop" not in text
    assert scrubbed["message"] == (
        "Payment failed for [card number] cvv [security code]"
    )


def test_sentry_masks_a_bot_token_before_its_digits() -> None:
    assert mask_personal_data("GET /bot123456789:fake-token-of-tests") == (
        "GET /bot<redacted>"
    )
