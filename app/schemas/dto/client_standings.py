"""The platform admin's client list as the stored client standings serve it."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.client_health import ClientHealthStatus
from app.schemas.constants.niches import NicheKey
from app.schemas.typings.client_health.constrained_integers import (
    ClientListPosition,
)
from app.schemas.typings.localization.constrained_strings import CountryCode


class ClientStandingFilter(ImmutableDTO):
    """The admin list's filters the database applies (None keeps every value)."""

    business_status: BusinessStatus | None = None
    health_status: ClientHealthStatus | None = None
    country_code: CountryCode | None = None
    niche_key: NicheKey | None = None


class ClientListPositions(ImmutableDTO):
    """Where a client stands in each order of the admin list (0 first)."""

    health: ClientListPosition
    name: ClientListPosition
    usage: ClientListPosition
    margin: ClientListPosition
    cost: ClientListPosition
    revenue: ClientListPosition


class ClientChoices(ImmutableDTO):
    """The countries and niches the platform's clients have (filter choices)."""

    countries: list[CountryCode] = Field(default_factory=list[CountryCode])
    niches: list[NicheKey] = Field(default_factory=list[NicheKey])
