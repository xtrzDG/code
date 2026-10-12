"""What the cabinet shows of a brand: its locations and its team."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.niches import NicheKey
from app.schemas.typings.brands.booleans import IsPrimaryBrandLocation
from app.schemas.typings.brands.prefixed_id import BrandId
from app.schemas.typings.brands.strings import BrandName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName, CityName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    E164PhoneNumber,
)
from app.schemas.typings.users.booleans import IsUserVerified
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import UserDisplayName


class BrandLocationView(ImmutableDTO):
    """
    A location of the brand. `is_primary` marks the oldest one, billed at
    its plan's price; every other location of the brand is billed at the
    plan's additional-location price.
    """

    business_id: BusinessId
    name: BusinessName
    city: CityName | None = None
    status: BusinessStatus
    niche_key: NicheKey
    plan_key: PlanKey
    country_code: CountryCode
    currency_code: CurrencyCode
    is_primary: IsPrimaryBrandLocation = False


class BrandMemberView(ImmutableDTO):
    """A person of the brand's team; `business_ids`: a manager's locations."""

    user_id: UserId
    role: BrandMemberRole
    business_ids: list[BusinessId] = Field(default_factory=list[BusinessId])
    display_name: UserDisplayName | None = None
    phone_number: E164PhoneNumber | None = None
    email: EmailAddress | None = None
    is_verified: IsUserVerified = False


class BrandView(ImmutableDTO):
    """
    A brand as one member sees it: `viewer_role` is theirs, `locations`
    those they reach (every one for a brand owner, the assigned ones for a
    regional manager). The team is listed to brand owners only (empty for
    a manager: other people's contacts are the owners' business).
    """

    id: BrandId
    name: BrandName
    viewer_role: BrandMemberRole
    locations: list[BrandLocationView] = Field(default_factory=list[BrandLocationView])
    members: list[BrandMemberView] = Field(default_factory=list[BrandMemberView])
    created_at: Microseconds
