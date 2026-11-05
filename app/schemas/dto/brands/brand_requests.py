"""HTTP bodies of the brand routes (`/v1/brands`)."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.brands import BrandMemberRole
from app.schemas.typings.brands.strings import BrandName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName, CityName
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.strings import RawEmailAddressInput, UserDisplayName


class CreateBrandRequest(ImmutableDTO):
    """
    A new brand and its first location, a business the creator owns; the
    creator becomes its owner.

    Example: {"name": "Mtsvane Ezo", "business_id": "business_…"}.
    """

    name: BrandName
    business_id: BusinessId


class RenameBrandRequest(ImmutableDTO):
    """A brand's new name."""

    name: BrandName


class AddBrandLocationRequest(ImmutableDTO):
    """A business the brand owner owns joins the brand as a location."""

    business_id: BusinessId


class CloneBrandLocationRequest(ImmutableDTO):
    """
    A new location made from one of the brand's: its profile, resources,
    knowledge and channel settings, never its channel tokens, payment
    settings, API keys, webhooks or customers. `city` defaults to none.

    Example: {"source_business_id": "business_…", "name": "Mtsvane Ezo Vake"}.
    """

    source_business_id: BusinessId
    name: BusinessName
    city: CityName | None = None


class InviteBrandMemberRequest(ImmutableDTO):
    """
    A person joins the brand's team by phone number (any country) or
    e-mail. A REGIONAL_MANAGER works in `business_ids` (locations of the
    brand) only; a BRAND_OWNER in every location (`business_ids` empty).

    Example: {"email": "nino@example.com", "role": "regional_manager",
    "business_ids": ["business_…"]}.
    """

    phone_number: RawPhoneNumberInput | None = None
    email: RawEmailAddressInput | None = None
    country_hint: CountryCode | None = None
    display_name: UserDisplayName | None = None
    role: BrandMemberRole = BrandMemberRole.REGIONAL_MANAGER
    business_ids: list[BusinessId] = Field(default_factory=list[BusinessId])


class ChangeBrandMemberRequest(ImmutableDTO):
    """A member's new role and, for a regional manager, their locations."""

    role: BrandMemberRole
    business_ids: list[BusinessId] = Field(default_factory=list[BusinessId])
