"""
The cabinet's value endpoints: the value of a period, the average check,
an owner's digest choices and the queue of today.
"""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.value import ValueBasis, ValuePeriod
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.notifications.booleans import IsProviderReady
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.value.booleans import (
    IsDailyDigestOn,
    IsMonthlyReportOn,
    IsWeeklyDigestOn,
)
from app.schemas.typings.value.constrained_integers import AverageCheckMinor


class BusinessValueQuery(ImmutableDTO):
    """
    The value of a period for a member: a named period (`period`), or local
    dates `date_from` to `date_to` (inclusive, at most 366 days), compared
    with as many days before them. Neither: the last 30 days.
    """

    user_id: UserId
    business_id: BusinessId
    period: ValuePeriod | None = None
    date_from: LocalDate | None = None
    date_to: LocalDate | None = None


class ValueSettingsRequest(ImmutableDTO):
    """
    The owner's average check, in minor units of the business currency;
    None clears it (the niche's typical check is used again).
    """

    average_check_minor: AverageCheckMinor | None = None


class ValueSettingsQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class UpdateValueSettingsCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    request: ValueSettingsRequest


class ValueSettingsView(ImmutableDTO):
    """
    The average check the owner set (None: not set), the niche's typical
    check in the business currency (None: unknown in this currency), and
    what earns money in the estimate (bookings, or requests for niches
    that take orders).
    """

    business_id: BusinessId
    currency_code: CurrencyCode
    average_check_minor: AverageCheckMinor | None = None
    typical_check_minor: AverageCheckMinor | None = None
    value_basis: ValueBasis


class DigestPreferencesRequest(ImmutableDTO):
    """
    Which summaries the signed-in owner gets: the daily digest (every
    morning), the weekly digest (Mondays) and the monthly report (the 1st).
    """

    is_daily_digest_on: IsDailyDigestOn = False
    is_weekly_digest_on: IsWeeklyDigestOn = True
    is_monthly_report_on: IsMonthlyReportOn = True


class DigestPreferencesQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class UpdateDigestPreferencesCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    request: DigestPreferencesRequest


class DigestPreferencesView(ImmutableDTO):
    """
    The owner's choices and where the summaries reach them: their sign-in
    e-mail (None: they sign in by phone) when the platform can send e-mail
    (`is_email_ready`), and their devices with notifications on in this
    business.
    """

    business_id: BusinessId
    is_daily_digest_on: IsDailyDigestOn
    is_weekly_digest_on: IsWeeklyDigestOn
    is_monthly_report_on: IsMonthlyReportOn
    email: EmailAddress | None = None
    is_email_ready: IsProviderReady
    device_count: ListItemCount


class TodayQueueQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class TodayQueue(ImmutableDTO):
    """
    Today's bookings of a business (local date, sandbox left out): those on
    (not cancelled, not a no-show), those still to start, and those waiting
    for confirmation. Counts only, no customer data.
    """

    business_id: BusinessId
    date: LocalDate
    booking_count: PeriodItemCount
    upcoming_booking_count: PeriodItemCount
    unconfirmed_booking_count: PeriodItemCount
