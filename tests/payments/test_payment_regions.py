"""Who charges a country, when retries are due, and Flitt's card fields."""

import pytest
from typed_time_provider import Microseconds

from app.adapters.payments.flitt_notification_reader import (
    read_card_expiry,
    read_flitt_event,
)
from app.registries.billing.payment_provider_registry import PaymentProviderRegistry
from app.registries.billing.payment_regions import (
    EUROPEAN_UNION_COUNTRY_CODES,
    regional_payment_provider,
)
from app.schemas.configurations.payment_settings import PaymentSettings
from app.schemas.constants.payments import PaymentProvider, PaymentStatus
from app.schemas.typings.billing.constrained_integers import PaymentRetryAttempt
from app.schemas.typings.billing.prefixed_id import InvoiceId
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    TimezoneName,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.billing.billing_periods import add_local_days
from app.utilities.billing.dunning_schedule import (
    find_due_attempt,
    find_grace_start,
    find_next_retry_at,
    list_earlier_attempts,
    retry_due_at,
)
from app.utilities.billing.payment_retry_identity import (
    derive_payment_retry_id,
    parse_payment_retry_id,
)
from tests.billing.billing_settings import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET

# 2026-10-20 09:00 in Berlin; the clocks go back on 2026-10-25.
DECLINED_AT: Microseconds = Microseconds(1_792_479_600_000_000)
BERLIN: TimezoneName = TimezoneName("Europe/Berlin")
HOUR: int = 3_600_000_000


def configured() -> PaymentSettings:
    return PaymentSettings(
        stripe_secret_key=PlatformSecret(STRIPE_SECRET_KEY),
        stripe_webhook_secret=PlatformSecret(STRIPE_WEBHOOK_SECRET),
    )


@pytest.mark.parametrize(
    ("country", "provider"),
    [
        ("GE", PaymentProvider.FLITT),
        ("AM", PaymentProvider.FLITT),
        ("DE", PaymentProvider.STRIPE),
        ("PL", PaymentProvider.STRIPE),
        ("IL", PaymentProvider.STRIPE),
        ("US", PaymentProvider.STRIPE),
        ("GB", PaymentProvider.FLITT),
        ("KZ", PaymentProvider.FLITT),
    ],
)
def test_each_region_has_its_provider(country: str, provider: PaymentProvider) -> None:
    assert regional_payment_provider(CountryCode(country)) is provider


def test_the_european_union_has_twenty_seven_members() -> None:
    assert len(EUROPEAN_UNION_COUNTRY_CODES) == 27


@pytest.mark.usefixtures("stripe_gate_open")
def test_stripe_is_chosen_only_when_configured() -> None:
    assert PaymentProviderRegistry(configured()).select(CountryCode("DE")) is (
        PaymentProvider.STRIPE
    )
    assert PaymentProviderRegistry(PaymentSettings()).select(CountryCode("DE")) is (
        PaymentProvider.FLITT
    )
    assert PaymentProviderRegistry(
        PaymentSettings(stripe_secret_key=PlatformSecret(STRIPE_SECRET_KEY))
    ).select(CountryCode("US")) is (PaymentProvider.FLITT)


def test_stripe_waits_for_its_release_gate() -> None:
    assert PaymentProviderRegistry(configured()).select(CountryCode("DE")) is (
        PaymentProvider.FLITT
    )


def test_retries_fall_on_local_days_one_three_and_six() -> None:
    grace_until = add_local_days(DECLINED_AT, 7, BERLIN)
    grace_start = find_grace_start(grace_until, 7, BERLIN)

    due = [
        retry_due_at(grace_start, PaymentRetryAttempt(attempt), BERLIN)
        for attempt in (1, 2, 3)
    ]

    assert grace_start == DECLINED_AT
    assert due[0] == DECLINED_AT + 24 * HOUR
    assert due[1] == DECLINED_AT + 3 * 24 * HOUR
    # Day 6 falls after the clocks go back: same local time, one hour later.
    assert due[2] == DECLINED_AT + (6 * 24 + 1) * HOUR
    assert find_due_attempt(grace_start, Microseconds(due[0] - 1), BERLIN) is None
    assert find_due_attempt(grace_start, due[0], BERLIN) == PaymentRetryAttempt(1)
    assert find_due_attempt(grace_start, Microseconds(due[2] + 1), BERLIN) == (
        PaymentRetryAttempt(3)
    )
    assert find_next_retry_at(grace_start, None, BERLIN) == due[0]
    assert find_next_retry_at(grace_start, PaymentRetryAttempt(2), BERLIN) == due[2]
    assert find_next_retry_at(grace_start, PaymentRetryAttempt(3), BERLIN) is None
    assert list_earlier_attempts(PaymentRetryAttempt(3)) == [
        PaymentRetryAttempt(1),
        PaymentRetryAttempt(2),
    ]


def test_a_retry_is_named_by_its_invoice_and_attempt() -> None:
    invoice_id = InvoiceId()

    first = derive_payment_retry_id(invoice_id, PaymentRetryAttempt(1))

    assert first == derive_payment_retry_id(invoice_id, PaymentRetryAttempt(1))
    assert first != derive_payment_retry_id(invoice_id, PaymentRetryAttempt(2))
    assert first != derive_payment_retry_id(InvoiceId(), PaymentRetryAttempt(1))
    assert parse_payment_retry_id(str(first)) == first
    assert parse_payment_retry_id(str(invoice_id)) is None
    assert parse_payment_retry_id(None) is None


@pytest.mark.parametrize(
    ("lifetime", "expected"),
    [
        ("01.12.2027 00:00:00", (12, 2027)),
        ("01.13.2027 00:00:00", None),
        ("2027-12-01", None),
        ("aa.bb.cccc", None),
        (None, None),
    ],
)
def test_the_card_expiry_comes_from_the_token_lifetime(
    lifetime: object, expected: tuple[int, int] | None
) -> None:
    expiry = read_card_expiry(lifetime)

    assert (None if expiry is None else (int(expiry[0]), int(expiry[1]))) == expected


def test_a_retry_callback_never_reports_a_new_card() -> None:
    retry_id = derive_payment_retry_id(InvoiceId(), PaymentRetryAttempt(2))

    event = read_flitt_event(
        {
            "order_id": str(retry_id),
            "order_status": "approved",
            "merchant_data": "payment_order_x",
            "amount": 51700,
            "currency": "GEL",
            "rectoken": "rectoken-test-0001",
            "masked_card": "444455XXXXXX1111",
        },
        DECLINED_AT,
    )

    assert event.payment is not None
    assert event.payment.is_retry
    assert event.payment.status is PaymentStatus.APPROVED
    assert event.payment_method is None


def test_a_card_without_a_lifetime_is_kept_without_expiry() -> None:
    event = read_flitt_event(
        {
            "order_id": "payment_order_x",
            "order_status": "approved",
            "amount": 0,
            "currency": "GEL",
            "rectoken": "  rectoken-test-0002 ",
            "card_type": "MASTERCARD",
        },
        DECLINED_AT,
    )

    assert event.payment_method is not None
    assert str(event.payment_method.card_token) == "rectoken-test-0002"
    summary = event.payment_method.summary
    assert summary is not None
    assert summary.last_digits is None
    assert summary.expiry_month is None
    assert str(summary.brand) == "MASTERCARD"
