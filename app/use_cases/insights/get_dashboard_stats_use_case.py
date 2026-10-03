"""The cabinet dashboard of a business for a period of local dates."""

from datetime import timedelta
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
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.operations.activity_counts import (
    ActivityPeriod,
    BookingActivityCount,
    ConversationMixCount,
    HandoffActivityCount,
)
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
from app.use_cases.insights.dashboard_activity import (
    ConversationActivity,
    DailyCounts,
    daily_bookings,
    daily_handoffs,
    fold_conversations,
    ranked_counts,
)
from app.use_cases.insights.dashboard_counts import (
    count_used_voice_minutes,
    share_percent,
)
from app.use_cases.insights.dashboard_package_usage import build_dashboard_package_usage
from app.use_cases.insights.dashboard_period import choose_dashboard_period
from app.use_cases.insights.dashboard_timeline import (
    TimelineStretch,
    build_timeline,
    timeline_period,
)
from app.use_cases.shared.business_access import require_business
from app.utilities.scheduling.opening_hours import DayRanges, business_day_ranges
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    local_day_start_microseconds,
    to_local_date,
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

    Everything is counted by the database (grouped counts over indexed
    columns, `dashboard_timeline` for days and opening hours), so the
    dashboard costs the same with a year of history as with a week.
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
        days: list[TimelineStretch] = build_timeline(date_from, date_to, zone, None)
        period_end: int = local_day_start_microseconds(
            date_to + timedelta(days=1), zone
        )
        by_day: ActivityPeriod = timeline_period(days, period_end)
        start: Microseconds = by_day.start
        end: Microseconds = by_day.end
        stretches: list[TimelineStretch] = build_timeline(
            date_from, date_to, zone, self._weekly_hours(business)
        )
        mix: list[ConversationMixCount] = self._conversation_repo.count_started_by_mix(
            business.id, start, end
        )
        conversations: ConversationActivity = fold_conversations(
            mix,
            self._conversation_repo.count_started_by_timeline(
                business.id, timeline_period(stretches, period_end)
            ),
            stretches,
        )
        bookings: list[BookingActivityCount] = self._booking_repo.count_made(
            business.id, by_day
        )
        handoffs: list[HandoffActivityCount] = self._handoff_repo.count_made(
            business.id, by_day
        )
        sandbox_ids: list[ConversationId] = (
            self._conversation_repo.list_sandbox_active_since(business.id, start)
        )
        booking_days: DailyCounts = daily_bookings(bookings)
        handoff_days: DailyCounts = daily_handoffs(handoffs)
        return DashboardStats(
            business_id=business.id,
            timezone=business.timezone,
            date_from=to_local_date(date_from),
            date_to=to_local_date(date_to),
            conversation_count=PeriodItemCount(conversations.total),
            customer_message_count=self._count_customer_messages(
                business, start, end, sandbox_ids
            ),
            after_hours_conversation_count=PeriodItemCount(conversations.after_hours),
            after_hours_share_percent=share_percent(
                conversations.after_hours, conversations.total
            ),
            booking_count=PeriodItemCount(sum(int(item.count) for item in bookings)),
            bookings_by_status=[
                BookingStatusCount(status=status, count=count)
                for status, count in ranked_counts(
                    (item.status, int(item.count)) for item in bookings
                )
            ],
            lead_count=self._lead_repo.count_made(business.id, start, end),
            handoff_count=PeriodItemCount(sum(int(item.count) for item in handoffs)),
            handoffs_by_reason=[
                HandoffReasonCount(reason=reason, count=count)
                for reason, count in ranked_counts(
                    (item.reason, int(item.count)) for item in handoffs
                )
            ],
            handoffs_by_urgency=[
                HandoffUrgencyCount(urgency=urgency, count=count)
                for urgency, count in ranked_counts(
                    (item.urgency, int(item.count)) for item in handoffs
                )
            ],
            languages=[
                LanguageCount(language=language, count=count)
                for language, count in ranked_counts(
                    (item.language, int(item.count))
                    for item in mix
                    if item.language is not None
                )
            ],
            channels=[
                ChannelCount(channel=channel, count=count)
                for channel, count in ranked_counts(
                    (item.channel, int(item.count)) for item in mix
                )
            ],
            open_unanswered_question_count=PeriodItemCount(
                int(self._unanswered_question_repo.count_open(business.id))
            ),
            used_voice_minutes=count_used_voice_minutes(
                self._usage_event_repo, business, int(start), int(end), set(sandbox_ids)
            ),
            daily=[
                DashboardDay(
                    date=to_local_date(date_from + timedelta(days=day)),
                    conversation_count=conversations.daily.on(day),
                    booking_count=booking_days.on(day),
                    handoff_count=handoff_days.on(day),
                )
                for day in range(len(days))
            ],
            package=build_dashboard_package_usage(
                self._subscription_repo,
                self._plan_registry,
                self._usage_event_repo,
                self._wall_clock,
                business,
            ),
        )

    def _weekly_hours(self, business: BusinessDocument) -> DayRanges | None:
        """The business's opening ranges by date; None without weekly hours."""

        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(business.id)
        )
        if profile is None or not profile.hours:
            return None

        return business_day_ranges(
            list(profile.hours),
            self._schedule_exception_repo.list_by_business(business.id),
        )

    def _count_customer_messages(
        self,
        business: BusinessDocument,
        start: Microseconds,
        end: Microseconds,
        sandbox_ids: list[ConversationId],
    ) -> PeriodItemCount:
        """Customer messages of the period outside sandbox conversations."""

        total: int = int(
            self._message_repo.count_customer_messages(business.id, start, end)
        )
        if sandbox_ids:
            total -= int(
                self._message_repo.count_customer_messages(
                    business.id, start, end, sandbox_ids
                )
            )

        return PeriodItemCount(total)
