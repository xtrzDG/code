"""Periodic job: the owners' daily and weekly digests and the monthly reports."""

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.value_repositories import (
    DigestPreferencesRepoContract,
    ValueReportRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.contracts.value import OwnerDigestFacilitatorContract
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.constants.value import ValueReportKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.value_reports import ValueReportDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.value.value_model import ValueModel, ValueModelQuery
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.value.constrained_integers import DigestRecipientCount
from app.use_cases.insights.value.value_access import value_model_query
from app.use_cases.insights.value.value_report_building import (
    build_value_report,
    delivered,
    had_activity,
)
from app.use_cases.insights.value.value_snapshots import build_value_report_view
from app.use_cases.shared.business_walk import walk_businesses
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    local_day_start_microseconds,
    microseconds_to_seconds,
    to_local_moment,
)
from app.utilities.value.digest_choices import wants_report
from app.utilities.value.value_keys import value_report_id_of
from app.utilities.value.value_periods import (
    ReportPeriod,
    is_report_due,
    report_period,
)

logger: logging.Logger = logging.getLogger(__name__)

# Digests are for businesses whose assistant answers customers; the monthly
# report also covers a month a paused business was live in.
REPORTING_STATUSES: dict[ValueReportKind, frozenset[BusinessStatus]] = {
    ValueReportKind.DAILY: frozenset({BusinessStatus.LIVE}),
    ValueReportKind.WEEKLY: frozenset({BusinessStatus.LIVE}),
    ValueReportKind.MONTHLY: frozenset({BusinessStatus.LIVE, BusinessStatus.PAUSED}),
}


class SendValueReportsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Hourly job over every business: from 09:00 local time, the daily
    digest (yesterday), the weekly digest (on Mondays, last week) and the
    monthly report (on the 1st, last month) are computed with the value
    model, stored, and sent to the owners who want them (e-mail and
    devices, in their language, with a link to the report).

    A period is reported once: the report's id derives from the business,
    kind and period, so a run after a restart, on another worker or after a
    failure finds it stored and moves on; the outbox queues each report
    once per recipient, so a run that died between queueing and storing
    queues nothing twice. A run that missed 09:00 catches up later the
    same day (daily), week (weekly) or month (monthly).

    Skipped: businesses that are not live (paused ones still get the
    monthly report), periods that ended before the business existed, and
    daily digests nobody turned on. A quiet period (no conversation,
    booking or request) is stored and not sent. One failing business never
    stops the others.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        value_report_repo: ValueReportRepoContract,
        digest_preferences_repo: DigestPreferencesRepoContract,
        compute_value_model: UseCaseContract[ValueModelQuery, ValueModel],
        owner_digests: OwnerDigestFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._value_report_repo: ValueReportRepoContract = value_report_repo
        self._digest_preferences_repo: DigestPreferencesRepoContract = (
            digest_preferences_repo
        )
        self._compute_value_model: UseCaseContract[ValueModelQuery, ValueModel] = (
            compute_value_model
        )
        self._owner_digests: OwnerDigestFacilitatorContract = owner_digests
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        stored: int = 0
        for business in walk_businesses(self._business_repo):
            try:
                stored += self._report(business)
            except Exception:
                logger.exception("Value reports of business %s failed.", business.id)

        return JobReport(processed_count=ProcessedItemCount(stored))

    def _report(self, business: BusinessDocument) -> int:
        now: Microseconds = self._wall_clock.now_unix()
        zone: ZoneInfo = load_time_zone(business.timezone)
        local_now: datetime = to_local_moment(microseconds_to_seconds(int(now)), zone)
        stored: int = 0
        for kind in ValueReportKind:
            if business.status not in REPORTING_STATUSES[kind] or not is_report_due(
                kind, local_now
            ):
                continue

            period: ReportPeriod = report_period(kind, local_now.date())
            if self._is_reportable(business, period, zone):
                stored += int(self._store_and_send(business, period, zone, now))

        return stored

    def _is_reportable(
        self,
        business: BusinessDocument,
        period: ReportPeriod,
        zone: ZoneInfo,
    ) -> bool:
        """Not stored yet, not before the business existed, wanted (daily)."""

        period_end: int = local_day_start_microseconds(
            period.dates.date_to + timedelta(days=1), zone
        )
        if period_end <= int(business.created_at):
            return False

        report_id = value_report_id_of(business.id, period.kind, period.period_key)
        if self._value_report_repo.get(business.id, report_id) is not None:
            return False

        return period.kind is not ValueReportKind.DAILY or any(
            wants_report(
                self._digest_preferences_repo.get(business.id, member.user_id),
                period.kind,
            )
            for member in business.members
            if member.role is BusinessMemberRole.OWNER
        )

    def _store_and_send(
        self,
        business: BusinessDocument,
        period: ReportPeriod,
        zone: ZoneInfo,
        now: Microseconds,
    ) -> bool:
        first_day: date = period.dates.date_from
        model: ValueModel = self._compute_value_model.run(
            value_model_query(business, period.dates)
        )
        report: ValueReportDocument = build_value_report(
            business,
            period,
            model,
            Microseconds(local_day_start_microseconds(first_day, zone)),
            now,
        )
        if had_activity(model.current):
            recipients: DigestRecipientCount = self._owner_digests.send(
                business, build_value_report_view(report)
            )
            report = delivered(report, recipients)

        return self._value_report_repo.insert_if_new(report)
