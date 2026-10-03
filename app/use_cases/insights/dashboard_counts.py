"""Counts of the dashboard: rankings, after-hours shares, voice minutes."""

from typed_time_provider import Microseconds

from app.contracts.repositories.billing_repositories import UsageEventRepoContract
from app.schemas.constants.billing import UsageKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.insights.constrained_floats import AfterHoursSharePercent
from app.schemas.typings.insights.constrained_integers import (
    UsedVoiceMinutes,
)
from app.utilities.scheduling.zoned_time import (
    SECONDS_PER_MINUTE,
)

SHARE_DECIMALS: int = 1


def share_percent(part: int, total: int) -> AfterHoursSharePercent:
    if total == 0:
        return AfterHoursSharePercent(0.0)

    return AfterHoursSharePercent(round(part * 100.0 / total, SHARE_DECIMALS))


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
