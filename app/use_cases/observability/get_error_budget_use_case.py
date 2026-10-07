from collections.abc import Sequence

from typed_time_provider import Microseconds, WallClock

from app.contracts.service_levels import (
    ServiceLevelHourRepoContract,
    ServiceLevelSlotRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.telemetry import ServiceLevelSeries
from app.schemas.domain.service_levels import ServiceLevelHourDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.dto.service_levels import (
    AnswerLatencyBudgetView,
    ErrorBudgetQuery,
    ErrorBudgetView,
    ObjectiveBudgetView,
    ServiceLevelTally,
)
from app.schemas.typings.observability.constrained_integers import (
    ServiceLevelEventCount,
    ServiceLevelHourCount,
)
from app.utilities.observability.service_levels import (
    ANSWER_P95_TARGET_MS,
    HOUR_MICROSECONDS,
    OBJECTIVES,
    SLO_WINDOW_HOURS,
    budget_left_permille,
    burn_rate_percent,
    hour_start_of,
    sum_slots,
)


class GetErrorBudgetUseCase(UseCaseContract[ErrorBudgetQuery, ErrorBudgetView]):
    """
    GET /v1/admin/system/error-budget, for a platform admin: the SLOs of
    docs/operations/slo.md over the hourly rows of the last 28 days. Each
    ratio objective shows its events, what is left of its error budget and
    how fast the slots of the last hour burned it; the answer latency
    objective shows the last hour's p95 and the hours that missed 15 s.
    One indexed read of at most 672 rows and two of twelve slots.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        slot_repo: ServiceLevelSlotRepoContract,
        hour_repo: ServiceLevelHourRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._slot_repo: ServiceLevelSlotRepoContract = slot_repo
        self._hour_repo: ServiceLevelHourRepoContract = hour_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ErrorBudgetQuery) -> ErrorBudgetView:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.VIEW_OPERATIONS,
            )
        )
        now: int = int(self._wall_clock.now_unix())
        since: int = int(hour_start_of(now)) - SLO_WINDOW_HOURS * HOUR_MICROSECONDS
        hours: list[ServiceLevelHourDocument] = self._hour_repo.list_since(
            Microseconds(since)
        )
        return ErrorBudgetView(
            objectives=[
                self._objective(series, hours, now) for series in ServiceLevelSeries
            ],
            latency=latency_budget(hours),
            measured_since=hours[0].hour_start if hours else None,
            measured_until=(
                Microseconds(int(hours[-1].hour_start) + HOUR_MICROSECONDS)
                if hours
                else None
            ),
        )

    def _objective(
        self,
        series: ServiceLevelSeries,
        hours: Sequence[ServiceLevelHourDocument],
        now: int,
    ) -> ObjectiveBudgetView:
        objective = OBJECTIVES[series]
        window: ServiceLevelTally = tally_hours(series, hours)
        last_hour: ServiceLevelTally = sum_slots(
            series,
            self._slot_repo.list_window(
                series,
                Microseconds(now - HOUR_MICROSECONDS),
                Microseconds(now + 1),
            ),
        )
        return ObjectiveBudgetView(
            series=series,
            objective=objective,
            events=window.total,
            good_events=window.good,
            budget_left_permille=budget_left_permille(window, objective),
            burn_rate_last_hour_percent=burn_rate_percent(last_hour, objective),
        )


def tally_hours(
    series: ServiceLevelSeries, hours: Sequence[ServiceLevelHourDocument]
) -> ServiceLevelTally:
    """A ratio series summed over hourly rows."""

    if series is ServiceLevelSeries.INBOUND_ANSWERED:
        return ServiceLevelTally(
            series=series,
            total=ServiceLevelEventCount(
                sum(int(hour.inbound_messages) for hour in hours)
            ),
            good=ServiceLevelEventCount(
                sum(int(hour.inbound_in_time) for hour in hours)
            ),
        )

    requests: int = sum(int(hour.api_requests) for hour in hours)
    errors: int = sum(int(hour.api_server_errors) for hour in hours)
    return ServiceLevelTally(
        series=series,
        total=ServiceLevelEventCount(requests),
        good=ServiceLevelEventCount(max(0, requests - errors)),
    )


def latency_budget(
    hours: Sequence[ServiceLevelHourDocument],
) -> AnswerLatencyBudgetView:
    measured: list[ServiceLevelHourDocument] = [
        hour for hour in hours if hour.reply_p95_ms is not None
    ]
    return AnswerLatencyBudgetView(
        target_ms=ANSWER_P95_TARGET_MS,
        last_hour_p95_ms=hours[-1].reply_p95_ms if hours else None,
        hours_over_target=ServiceLevelHourCount(
            sum(
                1
                for hour in measured
                if hour.reply_p95_ms is not None
                and int(hour.reply_p95_ms) > int(ANSWER_P95_TARGET_MS)
            )
        ),
        measured_hours=ServiceLevelHourCount(len(measured)),
    )
