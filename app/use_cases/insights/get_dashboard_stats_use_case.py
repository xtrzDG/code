"""The cabinet dashboard of a business for a period of local dates."""

from collections import Counter
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import (
    SubscriptionRepoContract,
    UsageEventRepoContract,
)
from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    HandoffRepoContract,
    LeadRepoContract,
    UnansweredQuestionRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    ScheduleExceptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.operations.dashboard import (
    BookingStatusCount,
    ChannelCount,
    DashboardDay,
    DashboardStats,
    DashboardStatsQuery,
    HandoffReasonCount,
    HandoffUrgencyCount,
    LanguageCount,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.use_cases.bookings.operations_support import require_business
from app.use_cases.insights.dashboard_counts import (
    count_after_hours,
    count_used_voice_minutes,
    ranked,
    share_percent,
)
from app.use_cases.insights.dashboard_package_usage import build_dashboard_package_usage
from app.use_cases.insights.dashboard_period import choose_dashboard_period
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    local_day_start_microseconds,
    microseconds_to_seconds,
    to_local_date,
    to_local_moment,
)


class GetDashboardStatsUseCase(UseCaseContract[DashboardStatsQuery, DashboardStats]):
    """
    Cabinet dashboard for local dates of the business time zone (inclusive,
    at most 366 days; the last 30 days by default).

    Counts what started in the period: conversations, customer messages,
    conversations outside opening hours (flagged by the conversation engine,
    or starting outside the weekly hours with holidays applied), bookings by
    status, leads, handoffs by reason and urgency, languages and channels,
    and per local day the conversations, bookings and handoffs (for the
    trend chart). Also the open unanswered questions, the voice package
    minutes used in the period, and the package of the current billing
    window (used and included minutes and dialogs, no prices), which staff
    see too. Sandbox activity is excluded everywhere.
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
        subscription_repo: SubscriptionRepoContract,
        plan_registry: PlanRegistryContract,
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
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._plan_registry: PlanRegistryContract = plan_registry
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: DashboardStatsQuery) -> DashboardStats:
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        zone: ZoneInfo = load_time_zone(business.timezone)
        date_from, date_to = choose_dashboard_period(
            input_data, zone, self._wall_clock.now_unix()
        )
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
        after_hours_count: int = count_after_hours(
            self._business_profile_repo,
            self._schedule_exception_repo,
            business,
            zone,
            conversations,
        )
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

        def local_day(moment: Microseconds) -> date:
            return to_local_moment(microseconds_to_seconds(int(moment)), zone).date()

        conversations_by_day: Counter[date] = Counter(
            local_day(conversation.created_at) for conversation in conversations
        )
        bookings_by_day: Counter[date] = Counter(
            local_day(booking.created_at) for booking in bookings
        )
        handoffs_by_day: Counter[date] = Counter(
            local_day(handoff.created_at) for handoff in handoffs
        )
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
            used_voice_minutes=count_used_voice_minutes(
                self._usage_event_repo,
                business,
                period_start,
                period_end,
                sandbox_conversation_ids,
            ),
            daily=[
                DashboardDay(
                    date=to_local_date(day),
                    conversation_count=PeriodItemCount(conversations_by_day[day]),
                    booking_count=PeriodItemCount(bookings_by_day[day]),
                    handoff_count=PeriodItemCount(handoffs_by_day[day]),
                )
                for day in (
                    date_from + timedelta(days=offset)
                    for offset in range((date_to - date_from).days + 1)
                )
            ],
            package=build_dashboard_package_usage(
                self._subscription_repo,
                self._plan_registry,
                self._usage_event_repo,
                self._wall_clock,
                business,
            ),
        )
