"""
Which summaries an owner wants (without stored choices: weekly and monthly)
and where they go (without stored channels: e-mail and devices).
"""

from app.schemas.constants.value import DigestChannel, ValueReportKind
from app.schemas.domain.value_settings import DigestPreferencesDocument


def wants_report(
    preferences: DigestPreferencesDocument | None,
    kind: ValueReportKind,
) -> bool:
    if preferences is None:
        return kind is not ValueReportKind.DAILY

    if kind is ValueReportKind.DAILY:
        return preferences.is_daily_digest_on

    if kind is ValueReportKind.WEEKLY:
        return preferences.is_weekly_digest_on

    return preferences.is_monthly_report_on


# Where the summaries go without stored channels: as version 1 sent them.
DEFAULT_DIGEST_CHANNELS: tuple[DigestChannel, ...] = (
    DigestChannel.EMAIL,
    DigestChannel.PUSH,
)


def digest_channels_of(
    preferences: DigestPreferencesDocument | None,
) -> tuple[DigestChannel, ...]:
    """The channels an owner chose, in a fixed order; e-mail and devices by default."""

    if preferences is None or preferences.channels is None:
        return DEFAULT_DIGEST_CHANNELS

    chosen: set[DigestChannel] = set(preferences.channels)
    return tuple(channel for channel in DigestChannel if channel in chosen)
