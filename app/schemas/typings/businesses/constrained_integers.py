"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class BusinessRevision(BaseConstrainedTypedInt):
    """
    How many times a business document has been saved; every save makes it
    one higher. The cabinet sends the revision it edited back with a
    settings change, so a change based on an older revision is refused
    instead of silently overwriting a newer save.

    Example:
        revision = BusinessRevision(7)
    """

    ge = 0


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
