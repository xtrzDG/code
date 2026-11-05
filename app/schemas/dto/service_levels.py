"""
The service level indicators in flight: API requests counted per slot by
the API processes, the source counts of the hourly rows, and the error
budget card of /admin/system.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.telemetry import ServiceLevelSeries
from app.schemas.typings.client_health.constrained_integers import (
    MeasuredReplyCount,
)
from app.schemas.typings.observability.constrained_floats import (
    ServiceLevelObjective,
)
from app.schemas.typings.observability.constrained_integers import (
    AnswerLatencyP95Milliseconds,
    BurnRatePercent,
    ErrorBudgetLeftPermille,
    ServiceLevelEventCount,
    ServiceLevelHourCount,
)
from app.schemas.typings.storage.constrained_integers import DocumentBucketIndex
from app.schemas.typings.users.prefixed_id import UserId


class ApiRequestSlotCount(ImmutableDTO):
    """The requests one API process answered in one slot, and its 5xx."""

    slot_start: Microseconds
    requests: ServiceLevelEventCount
    server_errors: ServiceLevelEventCount


class ApiRequestCounts(ImmutableDTO):
    """What an API process adds to the shared slots at one flush."""

    slots: list[ApiRequestSlotCount] = Field(default_factory=list[ApiRequestSlotCount])


class ServiceLevelTally(ImmutableDTO):
    """Events of one series in a window, and how many of them were good."""

    series: ServiceLevelSeries
    total: ServiceLevelEventCount
    good: ServiceLevelEventCount


class LatencyBucketTally(ImmutableDTO):
    """Assistant replies whose measured wait fell into one latency bucket."""

    bucket: DocumentBucketIndex
    count: MeasuredReplyCount


class ErrorBudgetQuery(ImmutableDTO):
    """GET /v1/admin/system/error-budget, by a platform admin."""

    user_id: UserId


class ObjectiveBudgetView(ImmutableDTO):
    """
    One ratio objective over the last 28 days of hourly rows: its events,
    the good ones, what is left of its error budget (1000 untouched, 0
    spent, below 0 overspent) and how fast the last hour burned it (100 is
    the pace that spends it in exactly 28 days).
    """

    series: ServiceLevelSeries
    objective: ServiceLevelObjective
    events: ServiceLevelEventCount
    good_events: ServiceLevelEventCount
    budget_left_permille: ErrorBudgetLeftPermille
    burn_rate_last_hour_percent: BurnRatePercent


class AnswerLatencyBudgetView(ImmutableDTO):
    """
    The answer latency objective (p95 under 15 s): the last complete hour's
    p95 and how many of the measured hours of 28 days missed it.
    """

    target_ms: AnswerLatencyP95Milliseconds
    last_hour_p95_ms: AnswerLatencyP95Milliseconds | None = None
    hours_over_target: ServiceLevelHourCount
    measured_hours: ServiceLevelHourCount


class ErrorBudgetView(ImmutableDTO):
    """
    The error budgets of the SLOs (docs/operations/slo.md) as the hourly
    rows of `record_sli` give them; `measured_since` is the oldest row of
    the 28 days, `measured_until` the end of the newest (None: no row yet).
    """

    objectives: list[ObjectiveBudgetView] = Field(
        default_factory=list[ObjectiveBudgetView]
    )
    latency: AnswerLatencyBudgetView
    measured_since: Microseconds | None = None
    measured_until: Microseconds | None = None
