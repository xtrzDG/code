"""The owners' funnel, their time to go live and where the tunnel lost them."""

from collections.abc import Sequence
from statistics import median

from app.schemas.constants.analytics import (
    FunnelStep,
    ProductEventName,
    TunnelStepKey,
)
from app.schemas.dto.analytics.growth_views import FunnelStepView, TunnelStepView
from app.schemas.typings.analytics.constrained_floats import ConversionPercent
from app.schemas.typings.analytics.constrained_integers import (
    OwnerCount,
    TimeToLiveSeconds,
)
from app.utilities.analytics.owner_journeys import OwnerJourney

MICROSECONDS_PER_SECOND: int = 1_000_000
# What reaching each funnel step means; SIGNED_UP is every owner.
FUNNEL_STEPS: dict[FunnelStep, frozenset[ProductEventName]] = {
    FunnelStep.SIGNED_UP: frozenset(),
    FunnelStep.BUSINESS_CREATED: frozenset({ProductEventName.BUSINESS_CREATED}),
    FunnelStep.LAUNCH_ATTEMPTED: frozenset(
        {
            ProductEventName.LAUNCH_SUCCEEDED,
            ProductEventName.LAUNCH_BLOCKED,
            ProductEventName.WENT_LIVE,
        }
    ),
    FunnelStep.WENT_LIVE: frozenset({ProductEventName.WENT_LIVE}),
    FunnelStep.CHANNEL_CONNECTED: frozenset({ProductEventName.CHANNEL_CONNECTED}),
    FunnelStep.FIRST_CONVERSATION: frozenset(
        {ProductEventName.FIRST_REAL_CONVERSATION}
    ),
    FunnelStep.PAID: frozenset({ProductEventName.SUBSCRIBED}),
}
LIVE_EVENTS: frozenset[ProductEventName] = frozenset(
    {ProductEventName.WENT_LIVE, ProductEventName.LAUNCH_SUCCEEDED}
)


def percent_of(part: int, whole: int) -> ConversionPercent | None:
    """part / whole in percent with two decimals; None for an empty whole."""

    if whole <= 0:
        return None

    return ConversionPercent(round(100.0 * part / whole, 2))


def build_funnel(journeys: Sequence[OwnerJourney]) -> list[FunnelStepView]:
    """
    Owners at each step who also reached every step before it, so the bars
    only shrink; each with its share of the sign-ups and of the step before.
    """

    remaining: list[OwnerJourney] = list(journeys)
    sign_ups: int = len(remaining)
    previous: int = sign_ups
    steps: list[FunnelStepView] = []
    for step, names in FUNNEL_STEPS.items():
        if names:
            remaining = [
                journey for journey in remaining if journey.reached(names) is not None
            ]

        count: int = len(remaining)
        steps.append(
            FunnelStepView(
                step=step,
                owners=OwnerCount(count),
                share_of_sign_ups=percent_of(count, sign_ups),
                share_of_previous=percent_of(count, previous),
            )
        )
        previous = count

    return steps


def median_time_to_live(
    journeys: Sequence[OwnerJourney],
) -> TimeToLiveSeconds | None:
    """The median time from sign-up to the first assistant going live."""

    durations: list[int] = []
    for journey in journeys:
        went_live = journey.reached([ProductEventName.WENT_LIVE])
        if went_live is not None:
            durations.append(max(0, int(went_live) - int(journey.signed_up_at)))

    if not durations:
        return None

    return TimeToLiveSeconds(int(median(durations)) // MICROSECONDS_PER_SECOND)


def build_tunnel(journeys: Sequence[OwnerJourney]) -> list[TunnelStepView]:
    """
    Per tunnel screen: owners who entered it, completed it (went on without
    skipping), skipped it, and stopped there: it is the furthest screen
    they entered and they never went live.
    """

    order: list[TunnelStepKey] = list(TunnelStepKey)
    stopped: dict[TunnelStepKey, int] = dict.fromkeys(order, 0)
    for journey in journeys:
        entered = journey.tunnel.get(ProductEventName.TUNNEL_STEP_ENTERED, frozenset())
        if not entered or journey.reached(LIVE_EVENTS) is not None:
            continue

        stopped[max(entered, key=order.index)] += 1

    def owners_with(name: ProductEventName, step: TunnelStepKey) -> set[str]:
        return {
            str(journey.user_id)
            for journey in journeys
            if step in journey.tunnel.get(name, frozenset())
        }

    views: list[TunnelStepView] = []
    for step in order:
        skipped = owners_with(ProductEventName.TUNNEL_STEP_SKIPPED, step)
        completed = owners_with(ProductEventName.TUNNEL_STEP_COMPLETED, step) - skipped
        views.append(
            TunnelStepView(
                step=step,
                entered=OwnerCount(
                    len(owners_with(ProductEventName.TUNNEL_STEP_ENTERED, step))
                ),
                completed=OwnerCount(len(completed)),
                skipped=OwnerCount(len(skipped)),
                stopped_here=OwnerCount(stopped[step]),
            )
        )

    return views
