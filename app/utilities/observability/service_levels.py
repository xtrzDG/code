"""
The arithmetic of the service levels (docs/operations/slo.md): slots and
hours, whether a customer message was answered in time, error budgets and
burn rates. Pure functions; times are UNIX microseconds.
"""

from collections.abc import Iterable, Mapping, Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.deliveries import InboundEventKind, InboundEventStatus
from app.schemas.constants.telemetry import ServiceLevelSeries
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.service_levels import ServiceLevelSlotDocument
from app.schemas.dto.service_levels import LatencyBucketTally, ServiceLevelTally
from app.schemas.typings.observability.constrained_floats import (
    ServiceLevelObjective,
)
from app.schemas.typings.observability.constrained_integers import (
    AnswerLatencyP95Milliseconds,
    BurnRatePercent,
    ErrorBudgetLeftPermille,
    ServiceLevelEventCount,
)
from app.utilities.client_health.reply_speed import (
    P95,
    REPLY_LATENCY_BUCKET_STARTS,
    percentile_of,
)

MICROSECONDS_PER_SECOND: int = 1_000_000
MICROSECONDS_PER_MINUTE: int = 60 * MICROSECONDS_PER_SECOND
SLOT_MICROSECONDS: int = 5 * MICROSECONDS_PER_MINUTE
HOUR_MICROSECONDS: int = 60 * MICROSECONDS_PER_MINUTE
# A customer message counts as answered in time with its reply or handoff
# within 60 s of arriving.
ANSWER_DEADLINE_MICROSECONDS: int = 60 * MICROSECONDS_PER_SECOND
SLO_WINDOW_HOURS: int = 28 * 24
ANSWER_P95_TARGET_MS: AnswerLatencyP95Milliseconds = AnswerLatencyP95Milliseconds(
    15_000
)
OBJECTIVES: Mapping[ServiceLevelSeries, ServiceLevelObjective] = {
    ServiceLevelSeries.INBOUND_ANSWERED: ServiceLevelObjective(0.995),
    ServiceLevelSeries.API_AVAILABILITY: ServiceLevelObjective(0.999),
}
ANSWERED_STATUSES: frozenset[InboundEventStatus] = frozenset(
    {InboundEventStatus.ANSWERED, InboundEventStatus.HANDED_OFF}
)
PERCENT: int = 100
PERMILLE: int = 1000
# The bounds of ErrorBudgetLeftPermille and BurnRatePercent.
LOWEST_BUDGET_LEFT: int = -100_000
HIGHEST_BURN_RATE: int = 100_000_000
LONGEST_P95_MS: int = 86_400_000


def slot_start_of(at: int) -> Microseconds:
    """The start of the five-minute slot that holds `at`."""

    return Microseconds(at - at % SLOT_MICROSECONDS)


def hour_start_of(at: int) -> Microseconds:
    return Microseconds(at - at % HOUR_MICROSECONDS)


def slot_key(series: ServiceLevelSeries, slot_start: Microseconds) -> str:
    """The storage key of a series' slot: `<series>:<slot_start>`."""

    return f"{series.value}:{int(slot_start)}"


def is_customer_message(event: InboundEventDocument) -> bool:
    return (
        event.kind is InboundEventKind.CUSTOMER_MESSAGE
        and event.business_id is not None
    )


def is_answered_in_time(event: InboundEventDocument) -> bool:
    """Answered or handed off, and processed within 60 s of arriving."""

    if event.status not in ANSWERED_STATUSES or event.processed_at is None:
        return False

    return (
        int(event.processed_at) - int(event.created_at) <= ANSWER_DEADLINE_MICROSECONDS
    )


def tally_answers(
    events: Iterable[InboundEventDocument],
) -> tuple[ServiceLevelEventCount, ServiceLevelEventCount]:
    """The customer messages among `events` and those answered in time."""

    messages: list[InboundEventDocument] = [
        event for event in events if is_customer_message(event)
    ]
    return (
        ServiceLevelEventCount(len(messages)),
        ServiceLevelEventCount(
            sum(1 for event in messages if is_answered_in_time(event))
        ),
    )


def sum_slots(
    series: ServiceLevelSeries, slots: Sequence[ServiceLevelSlotDocument]
) -> ServiceLevelTally:
    return ServiceLevelTally(
        series=series,
        total=ServiceLevelEventCount(sum(int(slot.total) for slot in slots)),
        good=ServiceLevelEventCount(sum(int(slot.good) for slot in slots)),
    )


def burn_rate_percent(
    tally: ServiceLevelTally, objective: ServiceLevelObjective
) -> BurnRatePercent:
    """
    How fast the window spent the error budget, in percent of the pace that
    spends it in exactly the objective's 28 days: the bad share of the
    events over the share the objective allows (0 without events).
    """

    total: int = int(tally.total)
    if total == 0:
        return BurnRatePercent(0)

    bad: int = total - int(tally.good)
    allowed: float = 1.0 - float(objective)
    rate: int = round(bad * PERCENT / (total * allowed))
    return BurnRatePercent(min(HIGHEST_BURN_RATE, max(0, rate)))


def budget_left_permille(
    tally: ServiceLevelTally, objective: ServiceLevelObjective
) -> ErrorBudgetLeftPermille:
    """What is left of the budget the window's events allow (1000 untouched)."""

    total: int = int(tally.total)
    if total == 0:
        return ErrorBudgetLeftPermille(PERMILLE)

    bad: int = total - int(tally.good)
    allowed_bad: float = total * (1.0 - float(objective))
    left: int = PERMILLE - round(bad * PERMILLE / allowed_bad)
    return ErrorBudgetLeftPermille(min(PERMILLE, max(LOWEST_BUDGET_LEFT, left)))


def answer_p95(
    tallies: Sequence[LatencyBucketTally],
) -> AnswerLatencyP95Milliseconds | None:
    """The 95th percentile of the replies' waits (None without replies)."""

    counts: dict[int, int] = {}
    for tally in tallies:
        index: int = int(tally.bucket)
        if index < len(REPLY_LATENCY_BUCKET_STARTS):
            counts[index] = counts.get(index, 0) + int(tally.count)

    if sum(counts.values()) == 0:
        return None

    return AnswerLatencyP95Milliseconds(min(LONGEST_P95_MS, percentile_of(counts, P95)))
