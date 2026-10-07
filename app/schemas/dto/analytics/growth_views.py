"""The owners' way to paying: funnel, tunnel, activation, trials, cohorts."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.analytics import FunnelStep, TunnelStepKey
from app.schemas.typings.analytics.booleans import IsPlatformAdminIncluded
from app.schemas.typings.analytics.constrained_floats import (
    CohortPayingPercent,
    ConversionPercent,
)
from app.schemas.typings.analytics.constrained_integers import (
    BusinessCount,
    OwnerCount,
    TimeToLiveSeconds,
    TrialCount,
)
from app.schemas.typings.analytics.constrained_strings import (
    AcquisitionSourceKey,
    CohortMonth,
    ReferralCode,
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
    """
    Owners from one acquisition source: sign-ups, live and paying today. A
    source whose links carried referral codes has a row per code
    (`referral_code`: a partner's or an inviting business's), so the
    founder sees which partner or invitation brought whom.
    """

    source: AcquisitionSourceKey
    referral_code: ReferralCode | None = None
    sign_ups: OwnerCount
    went_live: OwnerCount
    paying: OwnerCount


class BusinessFunnelStepView(ImmutableDTO):
    """
    Businesses created in the period at one step (and every step before
    it), their share of the businesses created and of the step before.
    """

    step: FunnelStep
    businesses: BusinessCount
    share_of_created: ConversionPercent | None = None
    share_of_previous: ConversionPercent | None = None


class BusinessTunnelStepView(ImmutableDTO):
    """
    One screen of the setup tunnel, counted per business (a setup that has
    not created its business yet counts once too): entered, went on,
    skipped, and stopped there without going live.
    """

    step: TunnelStepKey
    entered: BusinessCount
    completed: BusinessCount
    skipped: BusinessCount
    stopped_here: BusinessCount


class BusinessGrowthView(ImmutableDTO):
    """
    Every business created in the period, whoever created it: the
    `created` count, how many of them belong to owners who had one before
    (`by_returning_owners`, a second business), their funnel and tunnel.
    """

    created: BusinessCount
    by_returning_owners: BusinessCount
    funnel: list[BusinessFunnelStepView]
    tunnel: list[BusinessTunnelStepView]


class GrowthView(ImmutableDTO):
    """
    The funnel of the period's sign-ups and what explains it, and the
    business-level funnel and tunnel of every business created in the
    period. Owners who are platform admins (and their businesses) are left
    out unless `are_platform_admins_included`; `excluded_platform_admins`
    says how many of the period's sign-ups that left out, and
    `excluded_admin_businesses` how many of its businesses.
    """

    funnel: list[FunnelStepView]
    median_time_to_live_seconds: TimeToLiveSeconds | None = None
    activation: ActivationView
    trials: TrialConversionView
    tunnel: list[TunnelStepView]
    cohorts: list[CohortRowView]
    sources: list[SourceRowView]
    businesses: BusinessGrowthView | None = None
    are_platform_admins_included: IsPlatformAdminIncluded = False
    excluded_platform_admins: OwnerCount = OwnerCount(0)
    excluded_admin_businesses: BusinessCount = BusinessCount(0)
