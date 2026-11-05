"""
What a verified Flitt callback tells the platform: a payment's status, and
with the approval of a first payment or a card verification, the card it
saved (its token charges the card again for the retries of a declined
automatic charge). An automatic charge points to our order through
`parent_order_id`; a retry is sent under its own retry id and names our
order in the merchant data.
"""

from typed_time_provider import Microseconds

from app.adapters.payments.payment_fields import (
    read_failure_reason,
    read_money,
    read_reference,
)
from app.schemas.constants.payments import PaymentProvider, PaymentStatus
from app.schemas.domain.billing_profiles import PaymentCardSnapshot
from app.schemas.domain.payment_methods import PaymentMethodSummary
from app.schemas.dto.payments import (
    PaymentMethodNotice,
    PaymentNotification,
    VerifiedPaymentEvent,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.constrained_integers import (
    PaymentCardExpiryMonth,
    PaymentCardExpiryYear,
)
from app.schemas.typings.billing.strings import (
    PaymentCardToken,
    PaymentProviderReference,
)
from app.schemas.typings.invoicing.constrained_strings import PaymentCardLastDigits
from app.schemas.typings.invoicing.strings import PaymentCardBrand
from app.utilities.billing.payment_retry_identity import parse_payment_retry_id

MAX_CARD_BRAND_LENGTH: int = 30
CARD_DIGITS_KEPT: int = 4
FAILED_STATUSES: frozenset[PaymentStatus] = frozenset(
    {PaymentStatus.DECLINED, PaymentStatus.EXPIRED}
)
# `rectoken_lifetime` is "dd.mm.yyyy hh:mm:ss": the card's expiry.
LIFETIME_DATE_PARTS: int = 3


def read_flitt_event(
    parameters: dict[str, object], received_at: Microseconds
) -> VerifiedPaymentEvent:
    """
    Raises:
        ValidationFailedError: no order id, or an unknown order status.
    """

    order_reference: PaymentProviderReference | None = read_reference(
        parameters.get("order_id")
    )
    if order_reference is None:
        raise ValidationFailedError("Payment notification has no order id.")

    status: PaymentStatus = read_payment_status(parameters.get("order_status"))
    parent_order_reference: PaymentProviderReference | None = read_reference(
        parameters.get("parent_order_id")
    )
    is_retry: bool = is_retry_reference(order_reference)
    card: PaymentCardSnapshot | None = read_card(
        parameters.get("masked_card"), parameters.get("card_type")
    )
    payment_reference: PaymentProviderReference | None = read_reference(
        parameters.get("payment_id")
    )
    payment = PaymentNotification(
        provider=PaymentProvider.FLITT,
        order_reference=order_reference,
        parent_order_reference=parent_order_reference,
        merchant_reference=read_reference(parameters.get("merchant_data")),
        payment_reference=payment_reference,
        status=status,
        amount=read_money(parameters.get("amount"), parameters.get("currency")),
        failure_reason=(
            read_failure_reason(parameters.get("response_description"))
            if status in FAILED_STATUSES
            else None
        ),
        card=card,
        is_retry=is_retry,
    )
    card_token: object = parameters.get("rectoken")
    if (
        status is not PaymentStatus.APPROVED
        or parent_order_reference is not None
        or is_retry
        or not isinstance(card_token, str)
        or card_token.strip() == ""
    ):
        return VerifiedPaymentEvent(payment=payment)

    expiry: tuple[PaymentCardExpiryMonth, PaymentCardExpiryYear] | None = (
        read_card_expiry(parameters.get("rectoken_lifetime"))
    )
    return VerifiedPaymentEvent(
        payment=payment,
        payment_method=PaymentMethodNotice(
            provider=PaymentProvider.FLITT,
            order_reference=order_reference,
            event_reference=payment_reference or order_reference,
            summary=PaymentMethodSummary(
                provider=PaymentProvider.FLITT,
                brand=None if card is None else card.brand,
                last_digits=None if card is None else card.last_digits,
                expiry_month=None if expiry is None else expiry[0],
                expiry_year=None if expiry is None else expiry[1],
                saved_at=received_at,
            ),
            card_token=PaymentCardToken(card_token.strip()),
        ),
    )


def is_retry_reference(order_reference: PaymentProviderReference) -> bool:
    """A retry's charge is sent under the retry id as its order id."""

    return parse_payment_retry_id(order_reference) is not None


def read_payment_status(raw_status: object) -> PaymentStatus:
    try:
        return PaymentStatus(str(raw_status).strip().lower())
    except ValueError as error:
        raise ValidationFailedError(
            "Payment notification has an unknown order status."
        ) from error


def read_card(
    raw_masked_card: object, raw_card_type: object
) -> PaymentCardSnapshot | None:
    """
    The payment system and the last four digits of Flitt's masked card
    ("444455XXXXXX1111", "VISA"); nothing else of the card is kept.
    """

    last_digits: PaymentCardLastDigits | None = None
    if isinstance(raw_masked_card, str):
        tail: str = raw_masked_card.strip()[-CARD_DIGITS_KEPT:]
        if len(tail) == CARD_DIGITS_KEPT and tail.isascii() and tail.isdigit():
            last_digits = PaymentCardLastDigits(tail)

    brand: PaymentCardBrand | None = None
    if isinstance(raw_card_type, str) and raw_card_type.strip() != "":
        brand = PaymentCardBrand(raw_card_type.strip()[:MAX_CARD_BRAND_LENGTH])

    if last_digits is None and brand is None:
        return None

    return PaymentCardSnapshot(brand=brand, last_digits=last_digits)


def read_card_expiry(
    raw_lifetime: object,
) -> tuple[PaymentCardExpiryMonth, PaymentCardExpiryYear] | None:
    """Month and year of "01.12.2027 00:00:00", when well-formed."""

    if not isinstance(raw_lifetime, str):
        return None

    date_parts: list[str] = raw_lifetime.strip().split(" ")[0].split(".")
    if len(date_parts) != LIFETIME_DATE_PARTS or not all(
        part.isascii() and part.isdigit() for part in date_parts
    ):
        return None

    try:
        return (
            PaymentCardExpiryMonth(int(date_parts[1])),
            PaymentCardExpiryYear(int(date_parts[2])),
        )
    except ValueError:
        return None
