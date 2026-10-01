"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class ClosingMinuteOfDay(BaseConstrainedTypedInt):
    """
    Local minute when an opening interval ends (1..1440, 1440 is midnight).

    Example:
        closes_at = ClosingMinuteOfDay(23 * 60)
    """

    ge = 1
    le = 1440


class OpeningMinuteOfDay(BaseConstrainedTypedInt):
    """
    Local minute when an opening interval starts (0..1439).

    Example:
        opens_at = OpeningMinuteOfDay(9 * 60)
    """

    ge = 0
    le = 1439


class RecordingRetentionDays(BaseConstrainedTypedInt):
    """Days call recordings and transcripts are kept (concept default 90)."""

    ge = 1
    le = 3650


# Keep abc order for all non example types, if possible.
