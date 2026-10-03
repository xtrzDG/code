"""Package use from metered usage events: voice minutes and dialogs."""

from typed_time_provider import Microseconds

from app.schemas.constants.billing import UsageKind
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.dto.billing_ledger import PackageUsageTotals
from app.schemas.typings.billing.constrained_integers import (
    OverageVoiceMinutes,
    PackageUsagePercent,
    UsedDialogs,
    UsedVoiceMinutes,
)

SECONDS_IN_MINUTE: int = 60
FULL_PERCENT: int = 100


def summarize_package_usage(
    events: list[UsageEventDocument],
    period_start: Microseconds,
    period_end: Microseconds,
) -> PackageUsageTotals:
    """
    Voice minutes (the sum of VOICE_SECONDS, rounded up to whole minutes)
    and dialogs (the sum of DIALOG events) of events inside the window.
    """

    voice_seconds: int = 0
    dialogs: int = 0
    for event in events:
        if not period_start <= event.occurred_at < period_end:
            continue

        if event.kind is UsageKind.VOICE_SECONDS:
            voice_seconds += int(event.quantity)
        elif event.kind is UsageKind.DIALOG:
            dialogs += int(event.quantity)

    return PackageUsageTotals(
        period_start=period_start,
        period_end=period_end,
        used_voice_minutes=UsedVoiceMinutes(-(-voice_seconds // SECONDS_IN_MINUTE)),
        used_dialogs=UsedDialogs(dialogs),
    )


def compute_usage_percent(used: int, included: int) -> PackageUsagePercent | None:
    """Whole percent used (rounded down); None for an empty package."""

    if included <= 0:
        return None

    return PackageUsagePercent(used * FULL_PERCENT // included)


def compute_overage_minutes(
    used_voice_minutes: UsedVoiceMinutes,
    included_voice_minutes: int,
) -> OverageVoiceMinutes:
    """Minutes above the package, never negative."""

    return OverageVoiceMinutes(max(int(used_voice_minutes) - included_voice_minutes, 0))
