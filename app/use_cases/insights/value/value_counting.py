"""
The totals of one value period, counted by the database (grouped counts
over indexed columns, as the dashboard counts; no document is read).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    HandoffRepoContract,
    LeadRepoContract,
)
from app.contracts.repositories.campaign_repositories import (
    OriginBookingCountRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.value_repositories import ValueCountRepoContract
from app.schemas.constants.bookings import BookingOrigin, BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.value import ValueBasis
from app.schemas.dto.operations.activity_counts import (
    ActivityPeriod,
    BookingActivityCount,
    ConversationMixCount,
)
from app.schemas.dto.value.value_model import ValueTotals
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.value.constrained_integers import (
    AverageCheckMinor,
    StaffMinutesSaved,
    StaffSecondsPerCall,
    StaffSecondsPerReply,
)
from app.use_cases.insights.dashboard_activity import (
    ConversationActivity,
    fold_conversations,
)
from app.use_cases.insights.dashboard_timeline import (
    TimelineStretch,
    build_timeline,
    timeline_period,
)
from app.use_cases.insights.dashboard_values import EARNING_STATUSES
from app.use_cases.insights.value.growth_lines import GrowthLine, count_growth_lines
from app.use_cases.insights.value.value_money import (
    BookedMoney,
    MoneyEstimate,
    assistant_booked_money,
    estimate_money,
)
from app.utilities.scheduling.opening_hours import DayRanges
from app.utilities.scheduling.zoned_time import local_day_start_microseconds

SECONDS_PER_MINUTE: int = 60
# A count of some conversations' items (None: of every conversation).
type CountOf = Callable[[list[ConversationId] | None], int]


@dataclass(frozen=True)
class ValueSources:
    """The repositories the totals are counted from."""

    conversation_repo: ConversationRepoContract
    message_repo: MessageRepoContract
    booking_repo: BookingRepoContract
    lead_repo: LeadRepoContract
    handoff_repo: HandoffRepoContract
    value_count_repo: ValueCountRepoContract
    origin_booking_count_repo: OriginBookingCountRepoContract


@dataclass(frozen=True)
class ValueRates:
    """How counts turn into money and minutes for one business."""

    basis: ValueBasis
    average_check: AverageCheckMinor | None
    seconds_per_reply: StaffSecondsPerReply
    seconds_per_call: StaffSecondsPerCall
    currency_code: CurrencyCode


@dataclass(frozen=True)
class ValueWindow:
    """One period of local days of a business, with its opening hours."""

    business_id: BusinessId
    zone: ZoneInfo
    weekly_hours: DayRanges | None
    date_from: date
    date_to: date
    sandbox_ids: list[ConversationId]


def count_value_totals(
    sources: ValueSources,
    window: ValueWindow,
    rates: ValueRates,
) -> ValueTotals:
    business_id: BusinessId = window.business_id
    end: int = local_day_start_microseconds(
        window.date_to + timedelta(days=1), window.zone
    )
    stretches: list[TimelineStretch] = build_timeline(
        window.date_from, window.date_to, window.zone, window.weekly_hours
    )
    start: Microseconds = Microseconds(stretches[0].start)
    whole: ActivityPeriod = ActivityPeriod(
        start=start, end=Microseconds(end), segment_starts=(start,)
    )
    mix: list[ConversationMixCount] = sources.conversation_repo.count_started_by_mix(
        business_id, whole.start, whole.end
    )
    conversations: ConversationActivity = fold_conversations(
        mix,
        sources.conversation_repo.count_started_by_timeline(
            business_id, timeline_period(stretches, end)
        ),
        stretches,
    )
    made: list[BookingActivityCount] = sources.booking_repo.count_made(
        business_id, whole
    )
    by_staff: dict[BookingStatus, PeriodItemCount] = (
        sources.value_count_repo.count_bookings_made_by_staff(
            business_id, whole.start, whole.end
        )
    )
    assistant_bookings: int = sum(
        int(group.count) for group in made if group.status in EARNING_STATUSES
    ) - sum(int(by_staff.get(status, 0)) for status in EARNING_STATUSES)
    replies: int = without_sandbox(
        lambda ids: int(
            sources.value_count_repo.count_assistant_replies(
                business_id, whole.start, whole.end, ids
            )
        ),
        window.sandbox_ids,
    )
    calls: int = sum(
        int(group.count) for group in mix if group.channel is ChannelKind.PHONE
    )
    requests: int = int(
        sources.lead_repo.count_made(business_id, whole.start, whole.end)
    )
    earning_units: int = (
        max(assistant_bookings, 0) if rates.basis is ValueBasis.BOOKINGS else requests
    )
    booked: BookedMoney = assistant_booked_money(
        sources.booking_repo.sum_value_made(business_id, whole),
        sources.booking_repo.sum_value_made(business_id, whole, by_staff_only=True),
        rates.currency_code,
    )
    money: MoneyEstimate = estimate_money(
        rates.basis, earning_units, booked, rates.average_check
    )
    growth: dict[BookingOrigin, GrowthLine] = count_growth_lines(
        sources.origin_booking_count_repo,
        business_id,
        whole.start,
        whole.end,
        rates.currency_code,
    )
    return ValueTotals(
        conversation_count=PeriodItemCount(conversations.total),
        after_hours_conversation_count=PeriodItemCount(conversations.after_hours),
        customer_message_count=PeriodItemCount(
            without_sandbox(
                lambda ids: int(
                    sources.message_repo.count_customer_messages(
                        business_id, whole.start, whole.end, ids
                    )
                ),
                window.sandbox_ids,
            )
        ),
        assistant_reply_count=PeriodItemCount(replies),
        call_count=PeriodItemCount(calls),
        booking_count=PeriodItemCount(sum(int(group.count) for group in made)),
        assistant_booking_count=PeriodItemCount(max(assistant_bookings, 0)),
        request_count=PeriodItemCount(requests),
        handoff_count=PeriodItemCount(
            sum(
                int(group.count)
                for group in sources.handoff_repo.count_made(business_id, whole)
            )
        ),
        staff_minutes_saved=staff_minutes(replies, calls, rates),
        estimated_revenue_minor=money.estimated_revenue_minor,
        valued_booking_count=booked.count,
        booked_value_minor=money.booked_value_minor,
        revenue_source=money.revenue_source,
        waitlist_booking_count=growth[BookingOrigin.WAITLIST].count,
        waitlist_value_minor=growth[BookingOrigin.WAITLIST].value_minor,
        campaign_booking_count=growth[BookingOrigin.CAMPAIGN].count,
        campaign_value_minor=growth[BookingOrigin.CAMPAIGN].value_minor,
    )


def without_sandbox(
    count: CountOf,
    sandbox_ids: list[ConversationId],
) -> int:
    """A count of every conversation minus that of the sandbox ones."""

    total: int = count(None)
    if sandbox_ids:
        total -= count(sandbox_ids)

    return max(total, 0)


def staff_minutes(replies: int, calls: int, rates: ValueRates) -> StaffMinutesSaved:
    """Replies and calls times staff seconds each, in whole minutes (rounded)."""

    seconds: int = replies * int(rates.seconds_per_reply) + calls * int(
        rates.seconds_per_call
    )
    return StaffMinutesSaved((seconds + SECONDS_PER_MINUTE // 2) // SECONDS_PER_MINUTE)
