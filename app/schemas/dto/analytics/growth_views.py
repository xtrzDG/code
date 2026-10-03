"""The owners' way to paying: funnel, tunnel, activation, trials, cohorts."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.analytics import FunnelStep, TunnelStepKey
from app.schemas.typings.analytics.constrained_floats import (
    CohortPayingPercent,
    ConversionPercent,
)
from app.schemas.typings.analytics.constrained_integers import (
    OwnerCount,
    TimeToLiveSeconds,
    TrialCount,
)
from app.schemas.typings.analytics.constrained_strings import (
    AcquisitionSourceKey,
    CohortMonth,
)
from app.schemas.typings.client_health.constrained_integers import ClientCount


class FunnelStepView(ImmutableDTO):
    """
    Owners of the cohort at one step (and every step before it), their
    share of the sign-ups and of the step before.
    """

    step: FunnelStep
    owners: OwnerCount
    share_of_sign_ups: ConversionPercent | None = None
    share_of_previous: ConversionPercent | None = None


class TunnelStepView(ImmutableDTO):
    """
    One screen of the setup tunnel: owners who entered it, went on from it
    or skipped it, and who stopped there (it was the furthest screen they
    reached and they never went live).
    """

    step: TunnelStepKey
    entered: OwnerCount
    completed: OwnerCount
    skipped: OwnerCount
    stopped_here: OwnerCount


class ActivationView(ImmutableDTO):
    """
    Businesses created in the period that went live, got a channel and a
    real conversation within 7 days of their creation. Businesses younger
    than 7 days that are not activated yet are `pending`, not counted.
    """

    eligible: ClientCount
    activated: ClientCount
    pending: ClientCount
    rate: ConversionPercent | None = None


class TrialConversionView(ImmutableDTO):
    """
    Trials started in the period: how many ended, and how many of those
    became paid subscriptions.
    """

    started: TrialCount
    ended: TrialCount
    converted: TrialCount
    rate: ConversionPercent | None = None


class CohortRowView(ImmutableDTO):
    """
    Owners who signed up in one month: how many, how many went live, and
    the share with a paying business at the end of each month since
    (`paying[0]` is their sign-up month; months not over yet end today).
    """

    month: CohortMonth
    sign_ups: OwnerCount
    went_live: OwnerCount
    paying: list[CohortPayingPercent] = Field(default_factory=list[CohortPayingPercent])


class SourceRowView(ImmutableDTO):
    """Owners from one acquisition source: sign-ups, live and paying today."""

    source: AcquisitionSourceKey
    sign_ups: OwnerCount
    went_live: OwnerCount
    paying: OwnerCount


class GrowthView(ImmutableDTO):
    """The funnel of the period's sign-ups and what explains it."""

    funnel: list[FunnelStepView]
    median_time_to_live_seconds: TimeToLiveSeconds | None = None
    activation: ActivationView
    trials: TrialConversionView
    tunnel: list[TunnelStepView]
    cohorts: list[CohortRowView]
    sources: list[SourceRowView]
