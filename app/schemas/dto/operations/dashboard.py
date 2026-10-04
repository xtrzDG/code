"""
The dashboard: counts of bookings, leads, handoffs, languages and channels,
the daily series and the package usage.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.typings.billing.constrained_integers import (
    IncludedDialogs,
    IncludedVoiceMinutes,
    OverageVoiceMinutes,
    PackageUsagePercent,
    UsedDialogs,
)
from app.schemas.typings.billing.constrained_integers import (
    UsedVoiceMinutes as PackageUsedVoiceMinutes,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.insights.constrained_floats import AfterHoursSharePercent
from app.schemas.typings.insights.constrained_integers import (
    PeriodItemCount,
    UsedVoiceMinutes,
)
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.value.constrained_integers import BookedValueMinor


class DashboardStatsQuery(ImmutableDTO):
    """
    Dashboard for an inclusive range of local dates in the business time
    zone. Defaults to the last 30 days including today. `user_id` is the
    member asking: staff see no money (the booked values stay empty).
    """

    user_id: UserId
    business_id: BusinessId
    date_from: LocalDate | None = None
    date_to: LocalDate | None = None


class BookingStatusCount(ImmutableDTO):
    """Bookings with one status."""

    status: BookingStatus
    count: PeriodItemCount


class HandoffReasonCount(ImmutableDTO):
    """Handoffs with one reason."""

    reason: HandoffReason
    count: PeriodItemCount


class HandoffUrgencyCount(ImmutableDTO):
    """Handoffs with one urgency."""

    urgency: HandoffUrgency
    count: PeriodItemCount


class LanguageCount(ImmutableDTO):
    """Conversations held in one language."""

    language: LanguageTag
    count: PeriodItemCount


class ChannelCount(ImmutableDTO):
    """Conversations started in one channel."""

    channel: ChannelKind
    count: PeriodItemCount


class BookedValueTotal(ImmutableDTO):
    """
    What the bookings made in a period are worth in one currency (their
    service prices and stays' nightly rates), and how many carry a value.
    """

    currency_code: CurrencyCode
    value_minor: BookedValueMinor
    booking_count: PeriodItemCount


class DashboardDay(ImmutableDTO):
    """What started on one local day of the dashboard period."""

    date: LocalDate
    conversation_count: PeriodItemCount
    booking_count: PeriodItemCount
    handoff_count: PeriodItemCount


class DashboardPackageUsage(ImmutableDTO):
    """
    Use of the plan package in the current billing window, for owners and
    staff alike (no prices). Percents are empty for a package of zero.
    """

    period_start: Microseconds
    period_end: Microseconds
    used_voice_minutes: PackageUsedVoiceMinutes
    included_voice_minutes: IncludedVoiceMinutes
    voice_usage_percent: PackageUsagePercent | None = None
    overage_voice_minutes: OverageVoiceMinutes
    used_dialogs: UsedDialogs
    included_dialogs: IncludedDialogs
    dialog_usage_percent: PackageUsagePercent | None = None


class DashboardStats(ImmutableDTO):
    """
    Cabinet dashboard (concept /dashboard): conversations, customer messages,
    share started outside opening hours, bookings, leads, handoffs, languages,
    channels, open unanswered questions, package minutes used in the period,
    a series per local day, and the package of the current billing window
    (None without a subscription).

    `booked_value` is what the bookings made in the period are worth per
    currency (not cancelled, not a no-show; bookings without a priced
    service are left out), `after_hours_booked_value` the part booked while
    the business was closed by its weekly hours. Both stay empty for staff,
    who see no money.

    Sandbox (owner test and autotest) activity is excluded. Breakdown lists
    are ordered by count descending; `daily` has every date of the period,
    oldest first.
    """

    business_id: BusinessId
    timezone: TimezoneName
    date_from: LocalDate
    date_to: LocalDate
    conversation_count: PeriodItemCount
    customer_message_count: PeriodItemCount
    after_hours_conversation_count: PeriodItemCount
    after_hours_share_percent: AfterHoursSharePercent
    booking_count: PeriodItemCount
    bookings_by_status: list[BookingStatusCount] = Field(
        default_factory=list[BookingStatusCount]
    )
    lead_count: PeriodItemCount
    handoff_count: PeriodItemCount
    handoffs_by_reason: list[HandoffReasonCount] = Field(
        default_factory=list[HandoffReasonCount]
    )
    handoffs_by_urgency: list[HandoffUrgencyCount] = Field(
        default_factory=list[HandoffUrgencyCount]
    )
    languages: list[LanguageCount] = Field(default_factory=list[LanguageCount])
    channels: list[ChannelCount] = Field(default_factory=list[ChannelCount])
    open_unanswered_question_count: PeriodItemCount
    used_voice_minutes: UsedVoiceMinutes
    daily: list[DashboardDay] = Field(default_factory=list[DashboardDay])
    package: DashboardPackageUsage | None = None
    booked_value: list[BookedValueTotal] = Field(default_factory=list[BookedValueTotal])
    after_hours_booked_value: list[BookedValueTotal] = Field(
        default_factory=list[BookedValueTotal]
    )
