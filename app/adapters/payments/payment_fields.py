"""Fields of payment provider answers and notifications, read defensively."""

from typing import cast

from app.schemas.dto.billing import Money
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.billing.strings import (
    PaymentFailureReason,
    PaymentProviderReference,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode

MAX_FAILURE_REASON_LENGTH: int = 300


def read_mapping(raw_value: object) -> dict[str, object]:
    """A JSON object's fields, or none when it is anything else."""

    return cast(dict[str, object], raw_value) if isinstance(raw_value, dict) else {}


def read_reference(raw_value: object) -> PaymentProviderReference | None:
    """A provider identifier sent as text or number; empty means absent."""

    if isinstance(raw_value, bool) or raw_value is None:
        return None

    if isinstance(raw_value, int | str):
        text: str = str(raw_value).strip()
        return None if text == "" else PaymentProviderReference(text)

    return None


def read_money(raw_amount: object, raw_currency: object) -> Money | None:
    """Amount in minor units with its currency, when both are well-formed."""

    if isinstance(raw_amount, bool) or not isinstance(raw_currency, str):
        return None

    amount_text: str = (
        str(raw_amount).strip() if isinstance(raw_amount, int | str) else ""
    )
    if not amount_text.isdigit():
        return None

    try:
        return Money(
            amount_minor=MoneyAmountMinor(int(amount_text)),
            currency_code=CurrencyCode(raw_currency.strip().upper()),
        )
    except ValueError:
        return None


def read_failure_reason(raw_reason: object) -> PaymentFailureReason | None:
    if not isinstance(raw_reason, str) or raw_reason.strip() == "":
        return None

    return PaymentFailureReason(raw_reason.strip()[:MAX_FAILURE_REASON_LENGTH])
