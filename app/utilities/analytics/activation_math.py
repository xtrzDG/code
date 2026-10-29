"""Activation within a week, and free trials that turned into payments."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.analytics import ProductEventName
from app.schemas.dto.analytics.growth_views import ActivationView, TrialConversionView
from app.schemas.typings.analytics.constrained_integers import TrialCount
from app.schemas.typings.client_health.constrained_integers import ClientCount
from app.utilities.analytics.funnel_math import percent_of
from app.utilities.analytics.owner_journeys import BusinessJourney

ACTIVATION_WINDOW_MICROSECONDS: int = 7 * 24 * 60 * 60 * 1_000_000
# A business is activated when all of these happened within the window.
ACTIVATION_STEPS: tuple[ProductEventName, ...] = (
    ProductEventName.WENT_LIVE,
    ProductEventName.CHANNEL_CONNECTED,
    ProductEventName.FIRST_REAL_CONVERSATION,
)


def is_activated(business: BusinessJourney) -> bool:
    """Published, a channel and a real conversation within 7 days of creation."""

    deadline: int = int(business.created_at) + ACTIVATION_WINDOW_MICROSECONDS
    return all(
        step in business.first_at and int(business.first_at[step]) <= deadline
        for step in ACTIVATION_STEPS
    )


def build_activation(
    businesses: Sequence[BusinessJourney],
    period_start: Microseconds,
    period_end: Microseconds,
    now: Microseconds,
) -> ActivationView:
    """
    Businesses created in the period: activated ones, ones whose week is
    over without it (both eligible), and younger ones still on the way
    (pending, left out of the rate).
    """

    activated = eligible = pending = 0
    for business in businesses:
        if not int(period_start) <= int(business.created_at) < int(period_end):
            continue

        if is_activated(business):
            activated += 1
            eligible += 1
        elif int(now) >= int(business.created_at) + ACTIVATION_WINDOW_MICROSECONDS:
            eligible += 1
        else:
            pending += 1

    return ActivationView(
        eligible=ClientCount(eligible),
        activated=ClientCount(activated),
        pending=ClientCount(pending),
        rate=percent_of(activated, eligible),
    )


def build_trial_conversion(
    businesses: Sequence[BusinessJourney],
    period_start: Microseconds,
    period_end: Microseconds,
    now: Microseconds,
) -> TrialConversionView:
    """
    Trials started in the period; of those that ended by now, the ones the
    business paid for (a subscription after the trial started).
    """

    started = ended = converted = 0
    for business in businesses:
        trial_at = business.first_at.get(ProductEventName.TRIAL_STARTED)
        if trial_at is None or not int(period_start) <= int(trial_at) < int(period_end):
            continue

        started += 1
        if business.trial_ends_at is None or int(business.trial_ends_at) > int(now):
            continue

        ended += 1
        subscribed_at = business.first_at.get(ProductEventName.SUBSCRIBED)
        if subscribed_at is not None and int(subscribed_at) >= int(trial_at):
            converted += 1

    return TrialConversionView(
        started=TrialCount(started),
        ended=TrialCount(ended),
        converted=TrialCount(converted),
        rate=percent_of(converted, ended),
    )
