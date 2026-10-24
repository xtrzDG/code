"""
The business-level growth of the founder's metrics and who the platform
admin toggle leaves out.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.analytics.growth_views import BusinessGrowthView
from app.schemas.typings.analytics.constrained_integers import BusinessCount
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.metrics.metrics_period import MetricsPeriod
from app.utilities.analytics.business_funnel_math import (
    build_business_funnel,
    build_business_tunnel,
    count_returning,
    created_between,
    tunnel_units,
)
from app.utilities.analytics.owner_journeys import BusinessJourney, OwnerJourney


@dataclass(frozen=True)
class AdminExclusion:
    """The owners who are platform admins, and whether they count."""

    admin_ids: frozenset[UserId]
    is_included: bool

    def keeps_owner(self, owner_id: UserId | None) -> bool:
        return self.is_included or owner_id not in self.admin_ids

    def owners(self, journeys: Sequence[OwnerJourney]) -> list[OwnerJourney]:
        return [journey for journey in journeys if self.keeps_owner(journey.user_id)]

    def businesses(self, journeys: Sequence[BusinessJourney]) -> list[BusinessJourney]:
        return [journey for journey in journeys if self.keeps_owner(journey.owner_id)]


def admin_exclusion(
    people: Sequence[UserDocument], is_included: bool
) -> AdminExclusion:
    """Platform admins among these people (sign-ups and business owners)."""

    return AdminExclusion(
        admin_ids=frozenset(user.id for user in people if user.is_platform_admin),
        is_included=is_included,
    )


def build_business_growth(
    in_scope: Sequence[BusinessJourney],
    every: Sequence[BusinessJourney],
    events: Sequence[ProductEventDocument],
    cohort: Sequence[OwnerJourney],
    period: MetricsPeriod,
    exclusion: AdminExclusion,
) -> BusinessGrowthView:
    """
    Every business of the filters created in the period (owned by an admin
    only with the toggle), its funnel and tunnel; setups on their way count
    for the period's owners and the owners of the businesses in scope.
    """

    created: list[BusinessJourney] = exclusion.businesses(
        created_between(in_scope, period.start, period.end)
    )
    setup_owners: set[UserId] = {journey.user_id for journey in cohort}
    setup_owners.update(
        journey.owner_id
        for journey in exclusion.businesses(in_scope)
        if journey.owner_id is not None
    )
    return BusinessGrowthView(
        created=BusinessCount(len(created)),
        by_returning_owners=BusinessCount(count_returning(created, every)),
        funnel=build_business_funnel(created),
        tunnel=build_business_tunnel(
            tunnel_units(created, every, events, setup_owners)
        ),
    )


def count_excluded_businesses(
    in_scope: Sequence[BusinessJourney],
    period: MetricsPeriod,
    exclusion: AdminExclusion,
) -> BusinessCount:
    """Businesses of the period the toggle leaves out (owned by admins)."""

    if exclusion.is_included:
        return BusinessCount(0)

    created = created_between(in_scope, period.start, period.end)
    return BusinessCount(len(created) - len(exclusion.businesses(created)))
