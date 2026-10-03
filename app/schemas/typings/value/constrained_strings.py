"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class ValueReportPeriodKey(BaseConstrainedTypedString):
    """
    The period a value report summarizes: a local date ("2026-10-02", a
    daily digest), an ISO week ("2026-W40", a weekly digest) or a month
    ("2026-09", a monthly report).

    Example:
        period = ValueReportPeriodKey("2026-W40")
    """

    min_length = 7
    max_length = 10
    pattern = r"^\d{4}-(W\d{2}|\d{2}|\d{2}-\d{2})$"


# Keep abc order for all non example types, if possible.
