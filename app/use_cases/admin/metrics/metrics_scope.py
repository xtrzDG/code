"""Which owners and businesses the founder's filters keep."""

from collections.abc import Sequence

from app.schemas.constants.niches import NicheKey
from app.schemas.domain.users import UserDocument
from app.schemas.dto.analytics.admin_metrics_query import AdminMetricsQuery
from app.schemas.dto.analytics.admin_metrics_view import MetricsFilterChoices
from app.schemas.typings.analytics.constrained_strings import AcquisitionSourceKey
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.analytics.acquisition_sources import (
    UNKNOWN_SOURCE,
    acquisition_source_of,
)
from app.utilities.analytics.owner_journeys import BusinessJourney, OwnerJourney


def keeps_owner(journey: OwnerJourney, query: AdminMetricsQuery) -> bool:
    """
    The owner's country (of their first business, else of their phone),
    the niche of their first business (an owner without one has no niche)
    and their acquisition source match the filters.
    """

    return (
        (query.country_code is None or journey.country_code == query.country_code)
        and (query.niche_key is None or journey.niche_key is query.niche_key)
        and (query.source is None or journey.source == query.source)
    )


def owner_sources(owners: Sequence[UserDocument]) -> dict[UserId, AcquisitionSourceKey]:
    return {
        owner.id: acquisition_source_of(owner.signup_attribution) for owner in owners
    }


def business_scope(
    businesses: Sequence[BusinessJourney],
    sources: dict[UserId, AcquisitionSourceKey],
    query: AdminMetricsQuery,
) -> list[BusinessJourney]:
    """Businesses of the filtered country and niche whose owner came from
    the filtered source."""

    def source_of(business: BusinessJourney) -> AcquisitionSourceKey:
        if business.owner_id is None:
            return UNKNOWN_SOURCE
        return sources.get(business.owner_id, UNKNOWN_SOURCE)

    return [
        business
        for business in businesses
        if (query.country_code is None or business.country_code == query.country_code)
        and (query.niche_key is None or business.niche_key is query.niche_key)
        and (query.source is None or source_of(business) == query.source)
    ]


def filter_choices(
    businesses: Sequence[BusinessJourney],
    owners: Sequence[OwnerJourney],
    sources: dict[UserId, AcquisitionSourceKey],
) -> MetricsFilterChoices:
    countries: set[CountryCode] = {business.country_code for business in businesses}
    countries.update(owner.country_code for owner in owners if owner.country_code)
    niches: set[NicheKey] = {business.niche_key for business in businesses}
    found: set[AcquisitionSourceKey] = set(sources.values())
    found.update(owner.source for owner in owners)
    return MetricsFilterChoices(
        countries=sorted(countries, key=str),
        niches=sorted(niches, key=lambda niche: niche.value),
        sources=sorted(found, key=str),
    )


def business_ids(businesses: Sequence[BusinessJourney]) -> set[BusinessId]:
    return {business.business_id for business in businesses}
