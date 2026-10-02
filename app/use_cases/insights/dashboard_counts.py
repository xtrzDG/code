"""Counts of the dashboard: rankings, after-hours shares, voice minutes."""

from collections import Counter
from collections.abc import Hashable, Iterable
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.contracts.repositories.billing_repositories import UsageEventRepoContract
from app.contracts.repositories.business_repositories import BusinessProfileRepoContract
from app.contracts.repositories.knowledge_repositories import (
    ScheduleExceptionRepoContract,
)
from app.schemas.constants.billing import UsageKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.profiles import BusinessProfileDocument, OpeningInterval
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.insights.constrained_floats import AfterHoursSharePercent
from app.schemas.typings.insights.constrained_integers import (
    PeriodItemCount,
    UsedVoiceMinutes,
)
from app.utilities.scheduling.opening_hours import (
    DayRanges,
    business_day_ranges,
    is_open_at,
)
from app.utilities.scheduling.zoned_time import (
    SECONDS_PER_MINUTE,
    microseconds_to_seconds,
)

SHARE_DECIMALS: int = 1


def ranked[Key: Hashable](keys: Iterable[Key]) -> list[tuple[Key, PeriodItemCount]]:
    """Counts per key, largest first (ties in key order)."""

    counts: Counter[Key] = Counter(keys)
    return [
        (key, PeriodItemCount(count))
        for key, count in sorted(
            counts.items(), key=lambda item: (-item[1], str(item[0]))
        )
    ]


def share_percent(part: int, total: int) -> AfterHoursSharePercent:
    if total == 0:
        return AfterHoursSharePercent(0.0)

    return AfterHoursSharePercent(round(part * 100.0 / total, SHARE_DECIMALS))


def count_after_hours(
    business_profile_repo: BusinessProfileRepoContract,
    schedule_exception_repo: ScheduleExceptionRepoContract,
    business: BusinessDocument,
    zone: ZoneInfo,
    conversations: list[ConversationDocument],
) -> int:
    profile: BusinessProfileDocument | None = business_profile_repo.get_by_business(
        business.id
    )
    hours: list[OpeningInterval] = [] if profile is None else list(profile.hours)
    ranges_starting_on: DayRanges | None = (
        business_day_ranges(
            hours, schedule_exception_repo.list_by_business(business.id)
        )
        if hours
        else None
    )
    return sum(
        1
        for conversation in conversations
        if conversation.is_after_hours
        or (
            ranges_starting_on is not None
            and not is_open_at(
                microseconds_to_seconds(int(conversation.created_at)),
                zone,
                ranges_starting_on,
            )
        )
    )


def count_used_voice_minutes(
    usage_event_repo: UsageEventRepoContract,
    business: BusinessDocument,
    period_start: int,
    period_end: int,
    sandbox_conversation_ids: set[ConversationId],
) -> UsedVoiceMinutes:
    voice_seconds: int = sum(
        int(event.quantity)
        for event in usage_event_repo.list_by_business_between(
            business.id, Microseconds(period_start), Microseconds(period_end)
        )
        if event.kind is UsageKind.VOICE_SECONDS
        and event.conversation_id not in sandbox_conversation_ids
    )
    return UsedVoiceMinutes(-(-voice_seconds // SECONDS_PER_MINUTE))
