"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class ExchangeRateDate(BaseConstrainedTypedString):
    """
    Calendar day an official exchange rate was set for, ISO 8601 "YYYY-MM-DD".

    Example:
        nbg_rate_day = ExchangeRateDate("2026-09-30")
    """

    min_length = 10
    max_length = 10
    pattern = r"^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$"


# Keep abc order for all non example types, if possible.
