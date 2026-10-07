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


class CurrencyPairCode(BaseConstrainedTypedString):
    """
    A currency pair as rates are filed: base, a slash, quote (ISO 4217).

    Example:
        usd_to_gel = CurrencyPairCode("USD/GEL")
    """

    min_length = 7
    max_length = 7
    pattern = r"^[A-Z]{3}/[A-Z]{3}$"


class DiscountEndDate(BaseConstrainedTypedString):
    """
    The last local calendar day (in the business's time zone) a client's
    discount applies to: a period starting after it is billed in full.
    ISO 8601 "YYYY-MM-DD".

    Example:
        last_discounted_day = DiscountEndDate("2026-12-31")
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


class ExchangeRateValue(BaseConstrainedTypedString):
    """
    Units of the quote currency for one unit of the base currency, as an
    exact decimal string (> 0, at most 12 digits after the point), so rates
    are multiplied as `Decimal`, never as binary floats.

    Example:
        eur_to_gel = ExchangeRateValue("2.9552")
    """

    min_length = 1
    max_length = 25
    pattern = r"^(?=[0-9.]*[1-9])(0|[1-9][0-9]{0,11})(\.[0-9]{1,12})?$"


class ManualPaymentReference(BaseConstrainedTypedString):
    """
    What identifies money that came outside the payment provider: the bank
    transfer's reference or the cash receipt's number, as the founder reads
    it from the statement.

    Example:
        reference = ManualPaymentReference("TBC 2026-10-04 #88213")
    """

    min_length = 1
    max_length = 120
    pattern = r"^\S(.*\S)?$"


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
