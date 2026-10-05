"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class SpendDay(BaseConstrainedTypedString):
    """
    One calendar day of spend, ISO `YYYY-MM-DD`: a business's own day in its
    time zone (its daily limits), or a UTC day (the platform's spend).

    Example:
        day = SpendDay("2026-10-05")
    """

    min_length = 10
    max_length = 10
    pattern = r"^\d{4}-\d{2}-\d{2}$"
