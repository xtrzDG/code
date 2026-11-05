"""
Booking confirmations (of a booking, a cancellation, a move), reminders, a
deposit's line, reminders, refund terms and refund receipts, and the
waitlist's offer of a freed place (a utility template) are service
messages: none of their texts, in any language, carries a promotional
word, a discount code or a link written into it (`promotion_lint`).
Campaign texts are marketing and are not linted here: they go only with
consent, by day, in their own MARKETING template.
"""

from types import ModuleType

import pytest

from app.transformers.notifications import (
    booking_reminder_transformer,
    cancellation_confirmation_transformer,
    reschedule_confirmation_transformer,
)
from app.utilities.bookings import booking_confirmation_texts
from app.utilities.deposits import (
    deposit_line_texts,
    deposit_refund_terms,
    deposit_refund_terms_texts,
    deposit_refund_texts,
    deposit_reminder_texts,
)
from app.utilities.waitlist import waitlist_offer_texts
from tests.campaigns.promotion_lint import (
    lint_module,
    localized_texts,
    promotional_findings,
)

SERVICE_TEXT_MODULES: tuple[ModuleType, ...] = (
    booking_confirmation_texts,
    cancellation_confirmation_transformer,
    reschedule_confirmation_transformer,
    booking_reminder_transformer,
    deposit_line_texts,
    deposit_refund_terms,
    deposit_refund_terms_texts,
    deposit_refund_texts,
    deposit_reminder_texts,
    waitlist_offer_texts,
)


@pytest.mark.parametrize(
    "module", SERVICE_TEXT_MODULES, ids=lambda module: module.__name__
)
def test_service_texts_carry_no_promotion(module: ModuleType) -> None:
    assert list(localized_texts(module)), "the module defines no texts"
    assert lint_module(module) == {}


@pytest.mark.parametrize(
    ("text", "finding"),
    [
        ("Your booking is confirmed. 20% off your next visit!", "'% off'"),
        ("Prenotazione confermata. Approfitta dello sconto!", "'sconto'"),
        ("Бронь подтверждена. Скидка 10% по промокоду", "'скидк'"),
        ("Booking confirmed. Use code SPRING25 at checkout.", "'SPRING25'"),
        ("See our menu at https://example.com/menu", "a link"),
        ("Reminder: your table, see www.example.com", "a link"),
    ],
)
def test_the_linter_flags_promotion_codes_and_links(text: str, finding: str) -> None:
    assert any(finding in item for item in promotional_findings(text))


def test_the_linter_lets_a_service_text_and_its_placeholders_through() -> None:
    assert (
        promotional_findings(
            "Reminder: your booking at {business} is on {date} at {time}. "
            "Pay the deposit here: {link} Reference: {reference}."
        )
        == []
    )
