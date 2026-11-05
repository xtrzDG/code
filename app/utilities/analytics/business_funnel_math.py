"""
The business-level funnel and tunnel: every business created in the
period, a second business of an existing owner too (the owners' funnel
counts an owner once, by sign-up).

A business reaches a funnel step when it reached it and every step before
it. Its tunnel holds the tunnel steps reported with its id and, for the
first screens that come before the business exists, its owner's steps up
to its creation (after the owner's previous business). An owner's steps
after their last business are a setup still on its way: one unit more of
the tunnel, never live.
"""

from collections import defaultdict
from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.analytics import FunnelStep, ProductEventName, TunnelStepKey
from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.dto.analytics.growth_views import (
    BusinessFunnelStepView,
    BusinessTunnelStepView,
)
from app.schemas.typings.analytics.constrained_integers import BusinessCount
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.analytics.funnel_math import FUNNEL_STEPS, LIVE_EVENTS, percent_of
from app.utilities.analytics.owner_journeys import TUNNEL_EVENTS, BusinessJourney
from app.utilities.analytics.tunnel_math import TunnelUnit, count_tunnel

type StepSets = dict[ProductEventName, set[TunnelStepKey]]


def created_between(
    journeys: Sequence[BusinessJourney], start: Microseconds, end: Microseconds
) -> list[BusinessJourney]:
    """The businesses created from `start` until before `end`."""

    return [
        journey
        for journey in journeys
        if int(start) <= int(journey.created_at) < int(end)
    ]


def count_returning(
    created: Sequence[BusinessJourney], every: Sequence[BusinessJourney]
) -> int:
    """Businesses whose owner already had another one when they were made."""

    first_of: dict[UserId, int] = {}
    for journey in every:
        if journey.owner_id is not None:
            known = first_of.get(journey.owner_id)
            created_at = int(journey.created_at)
            first_of[journey.owner_id] = (
                created_at if known is None else min(known, created_at)
            )

    return sum(
        1
        for journey in created
        if journey.owner_id is not None
        and first_of.get(journey.owner_id, int(journey.created_at))
        < int(journey.created_at)
    )


def build_business_funnel(
    journeys: Sequence[BusinessJourney],
) -> list[BusinessFunnelStepView]:
    """The funnel's steps after sign-up, each business counted once."""

    remaining: list[BusinessJourney] = list(journeys)
    created: int = len(remaining)
    previous: int = created
    steps: list[BusinessFunnelStepView] = []
    for step, names in FUNNEL_STEPS.items():
        if step is FunnelStep.SIGNED_UP:
            continue

        remaining = [
            journey
            for journey in remaining
            if any(name in journey.first_at for name in names)
        ]
        count: int = len(remaining)
        steps.append(
            BusinessFunnelStepView(
                step=step,
                businesses=BusinessCount(count),
                share_of_created=percent_of(count, created),
                share_of_previous=percent_of(count, previous),
            )
        )
        previous = count

    return steps


def tunnel_units(
    created: Sequence[BusinessJourney],
    every: Sequence[BusinessJourney],
    events: Sequence[ProductEventDocument],
    setup_owners: set[UserId],
) -> list[TunnelUnit]:
    """
    A unit per business created, and one per owner of `setup_owners` whose
    last tunnel steps came after their last business (a setup on its way).
    """

    owned: dict[UserId, list[BusinessJourney]] = defaultdict(list)
    for journey in sorted(every, key=lambda item: int(item.created_at)):
        if journey.owner_id is not None:
            owned[journey.owner_id].append(journey)

    by_business: dict[BusinessId, StepSets] = defaultdict(lambda: defaultdict(set))
    on_the_way: dict[UserId, StepSets] = defaultdict(lambda: defaultdict(set))
    for event in events:
        step = event.properties.tunnel_step
        if event.name not in TUNNEL_EVENTS or step is None:
            continue

        business_id = event.business_id or business_after(event, owned)
        if business_id is not None:
            by_business[business_id][event.name].add(step)
        elif event.user_id is not None:
            on_the_way[event.user_id][event.name].add(step)

    units: list[TunnelUnit] = [
        TunnelUnit(
            key=str(journey.business_id),
            tunnel=frozen(by_business.get(journey.business_id, {})),
            is_live=any(name in journey.first_at for name in LIVE_EVENTS),
        )
        for journey in created
    ]
    units.extend(
        TunnelUnit(key=f"setup:{owner_id}", tunnel=frozen(steps))
        for owner_id, steps in sorted(on_the_way.items(), key=lambda item: item[0])
        if owner_id in setup_owners
    )
    return units


def business_after(
    event: ProductEventDocument, owned: dict[UserId, list[BusinessJourney]]
) -> BusinessId | None:
    """The owner's first business created at or after the step, if any."""

    if event.user_id is None:
        return None

    for journey in owned.get(event.user_id, []):
        if int(journey.created_at) >= int(event.occurred_at):
            return journey.business_id

    return None


def build_business_tunnel(units: Sequence[TunnelUnit]) -> list[BusinessTunnelStepView]:
    return [
        BusinessTunnelStepView(
            step=counts.step,
            entered=BusinessCount(counts.entered),
            completed=BusinessCount(counts.completed),
            skipped=BusinessCount(counts.skipped),
            stopped_here=BusinessCount(counts.stopped_here),
        )
        for counts in count_tunnel(units)
    ]


def frozen(
    steps: StepSets | dict[ProductEventName, set[TunnelStepKey]],
) -> dict[ProductEventName, frozenset[TunnelStepKey]]:
    return {name: frozenset(keys) for name, keys in steps.items()}
