from collections import Counter
from collections.abc import Hashable, Iterable
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories import (
    BookingRepoContract,
    BusinessProfileRepoContract,
    BusinessRepoContract,
    ConversationRepoContract,
    HandoffRepoContract,
    LeadRepoContract,
    MessageRepoContract,
    ScheduleExceptionRepoContract,
    UnansweredQuestionRepoContract,
    UsageEventRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.profiles import BusinessProfileDocument, OpeningInterval
from app.schemas.dto.operations import (
    BookingStatusCount,
    ChannelCount,
    DashboardStats,
    DashboardStatsQuery,
    HandoffReasonCount,
    HandoffUrgencyCount,
    LanguageCount,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.insights.constrained_floats import AfterHoursSharePercent
from app.schemas.typings.insights.constrained_integers import (
    PeriodItemCount,
    UsedVoiceMinutes,
)
from app.use_cases.bookings.operations_support import require_business
from app.utilities.scheduling.opening_hours import (
    DayRanges,
    business_day_ranges,
    is_open_at,
)
from app.utilities.scheduling.zoned_time import (
    SECONDS_PER_MINUTE,
    load_time_zone,
    local_day_start_microseconds,
    microseconds_to_seconds,
    parse_local_date,
    to_local_date,
    to_local_moment,
)

DEFAULT_PERIOD_DAYS: int = 30
MAX_PERIOD_DAYS: int = 366
SHARE_DECIMALS: int = 1


class GetDashboardStatsUseCase(UseCaseContract[DashboardStatsQuery, DashboardStats]):
    """
    Cabinet dashboard for local dates of the business time zone (inclusive,
    at most 366 days; the last 30 days by default).

    Counts what started in the period: conversations, customer messages,
    conversations outside opening hours (flagged by the conversation engine,
    or starting outside the weekly hours with holidays applied), bookings by
    status, leads, handoffs by reason and urgency, languages and channels.
    Also the open unanswered questions and the voice package minutes used.
    Sandbox activity is excluded everywhere.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        schedule_exception_repo: ScheduleExceptionRepoContract,
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        booking_repo: BookingRepoContract,
        lead_repo: LeadRepoContract,
        handoff_repo: HandoffRepoContract,
        unanswered_question_repo: UnansweredQuestionRepoContract,
        usage_event_repo: UsageEventRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._schedule_exception_repo: ScheduleExceptionRepoContract = (
            schedule_exception_repo
        )
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._lead_repo: LeadRepoContract = lead_repo
        self._handoff_repo: HandoffRepoContract = handoff_repo
        self._unanswered_question_repo: UnansweredQuestionRepoContract = (
            unanswered_question_repo
        )
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: DashboardStatsQuery) -> DashboardStats:
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        zone: ZoneInfo = load_time_zone(business.timezone)
        date_from, date_to = self._period(input_data, zone)
        period_start: int = local_day_start_microseconds(date_from, zone)
        period_end: int = local_day_start_microseconds(
            date_to + timedelta(days=1), zone
        )

        def in_period(moment: Microseconds) -> bool:
            return period_start <= int(moment) < period_end

        all_conversations: list[ConversationDocument] = (
            self._conversation_repo.list_by_business(business.id)
        )
        sandbox_conversation_ids: set[ConversationId] = {
            conversation.id
            for conversation in all_conversations
            if conversation.is_sandbox
        }
        conversations: list[ConversationDocument] = [
            conversation
            for conversation in all_conversations
            if not conversation.is_sandbox and in_period(conversation.created_at)
        ]
        after_hours_count: int = self._count_after_hours(business, zone, conversations)
        bookings = [
            booking
            for booking in self._booking_repo.list_by_business(business.id)
            if not booking.is_sandbox and in_period(booking.created_at)
        ]
        handoffs = [
            handoff
            for handoff in self._handoff_repo.list_by_business(business.id)
            if not handoff.is_sandbox and in_period(handoff.created_at)
        ]
        return DashboardStats(
            business_id=business.id,
            timezone=business.timezone,
            date_from=to_local_date(date_from),
            date_to=to_local_date(date_to),
            conversation_count=PeriodItemCount(len(conversations)),
            customer_message_count=PeriodItemCount(
                sum(
                    1
                    for message in self._message_repo.list_by_business(business.id)
                    if message.author is MessageAuthor.CUSTOMER
                    and message.conversation_id not in sandbox_conversation_ids
                    and in_period(message.created_at)
                )
            ),
            after_hours_conversation_count=PeriodItemCount(after_hours_count),
            after_hours_share_percent=share_percent(
                after_hours_count, len(conversations)
            ),
            booking_count=PeriodItemCount(len(bookings)),
            bookings_by_status=[
                BookingStatusCount(status=status, count=count)
                for status, count in ranked(booking.status for booking in bookings)
            ],
            lead_count=PeriodItemCount(
                sum(
                    1
                    for lead in self._lead_repo.list_by_business(business.id)
                    if not lead.is_sandbox and in_period(lead.created_at)
                )
            ),
            handoff_count=PeriodItemCount(len(handoffs)),
            handoffs_by_reason=[
                HandoffReasonCount(reason=reason, count=count)
                for reason, count in ranked(handoff.reason for handoff in handoffs)
            ],
            handoffs_by_urgency=[
                HandoffUrgencyCount(urgency=urgency, count=count)
                for urgency, count in ranked(handoff.urgency for handoff in handoffs)
            ],
            languages=[
                LanguageCount(language=language, count=count)
                for language, count in ranked(
                    conversation.language
                    for conversation in conversations
                    if conversation.language is not None
                )
            ],
            channels=[
                ChannelCount(channel=channel, count=count)
                for channel, count in ranked(
                    conversation.channel for conversation in conversations
                )
            ],
            open_unanswered_question_count=PeriodItemCount(
                sum(
                    1
                    for question in self._unanswered_question_repo.list_by_business(
                        business.id
                    )
                    if not question.is_resolved and not question.is_sandbox
                )
            ),
            used_voice_minutes=self._used_voice_minutes(
                business,
                period_start,
                period_end,
                sandbox_conversation_ids,
            ),
        )

    def _period(self, query: DashboardStatsQuery, zone: ZoneInfo) -> tuple[date, date]:
        today: date = to_local_moment(
            microseconds_to_seconds(int(self._wall_clock.now_unix())), zone
        ).date()
        date_to: date = (
            today if query.date_to is None else parse_local_date(query.date_to)
        )
        date_from: date = (
            date_to - timedelta(days=DEFAULT_PERIOD_DAYS - 1)
            if query.date_from is None
            else parse_local_date(query.date_from)
        )
        if date_from > date_to:
            raise ValidationFailedError("The start date is after the end date.")

        if (date_to - date_from).days + 1 > MAX_PERIOD_DAYS:
            raise ValidationFailedError(
                f"The period may be at most {MAX_PERIOD_DAYS} days long."
            )

        return date_from, date_to

    def _count_after_hours(
        self,
        business: BusinessDocument,
        zone: ZoneInfo,
        conversations: list[ConversationDocument],
    ) -> int:
        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(business.id)
        )
        hours: list[OpeningInterval] = [] if profile is None else list(profile.hours)
        ranges_starting_on: DayRanges | None = (
            business_day_ranges(
                hours, self._schedule_exception_repo.list_by_business(business.id)
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

    def _used_voice_minutes(
        self,
        business: BusinessDocument,
        period_start: int,
        period_end: int,
        sandbox_conversation_ids: set[ConversationId],
    ) -> UsedVoiceMinutes:
        voice_seconds: int = sum(
            int(event.quantity)
            for event in self._usage_event_repo.list_by_business_between(
                business.id, Microseconds(period_start), Microseconds(period_end)
            )
            if event.kind is UsageKind.VOICE_SECONDS
            and event.conversation_id not in sandbox_conversation_ids
        )
        return UsedVoiceMinutes(-(-voice_seconds // SECONDS_PER_MINUTE))


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
