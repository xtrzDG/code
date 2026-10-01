"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class AutoDebitStartDate(BaseConstrainedTypedString):
    """
    Local calendar day of the first automatic charge, ISO 8601 "YYYY-MM-DD".

    Example:
        first_charge_day = AutoDebitStartDate("2026-11-01")
    """

    min_length = 10
    max_length = 10
    pattern = r"^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$"


class ExchangeRateDate(BaseConstrainedTypedString):
    """
    Calendar day an official exchange rate was set for, ISO 8601 "YYYY-MM-DD".

    Example:
        nbg_rate_day = ExchangeRateDate("2026-09-30")
    """

    min_length = 10
    max_length = 10
    pattern = r"^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$"


class PaymentCheckoutUrl(BaseConstrainedTypedString):
    """
    Hosted payment page of the payment provider the owner is sent to.

    Example:
        checkout_url = PaymentCheckoutUrl("https://pay.flitt.com/merchants/abc")
    """

    min_length = 10
    max_length = 2048
    pattern = r"^https?://[^\s/]+(/[^\s]*)?$"


class PaymentReturnUrl(BaseConstrainedTypedString):
    """
    Cabinet page the payer's browser returns to after the payment page.

    Example:
        return_url = PaymentReturnUrl("https://app.example.com/billing")
    """

    min_length = 10
    max_length = 2048
    pattern = r"^https?://[^\s/]+(/[^\s]*)?$"


# Keep abc order for all non example types, if possible.
