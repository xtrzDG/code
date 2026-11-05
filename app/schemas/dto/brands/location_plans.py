"""The plans as one location of a brand would pay for them (R17)."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.dto.catalog.plan_quotes import PlanQuoteList
from app.schemas.typings.brands.booleans import (
    IsAdditionalLocation,
    IsBrandSetupFeeCovered,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.users.prefixed_id import UserId


class LocationPlanQuery(ImmutableDTO):
    """An owner opens the plans of a business (the cabinet's billing page)."""

    user_id: UserId
    business_id: BusinessId
    display_language: LanguageTag | None = None


class LocationPricing(ImmutableDTO):
    """
    How a business pays for a plan now: the country it is priced in, the
    language of the texts, whether it is a further location of its brand
    (the additional-location price a month) and whether its brand's one
    setup fee is carried by another location (none here).
    """

    business_id: BusinessId
    country_code: CountryCode
    display_language: LanguageTag
    is_additional_location: IsAdditionalLocation = False
    is_setup_fee_covered: IsBrandSetupFeeCovered = False


class LocationPlanQuoteList(PlanQuoteList):
    """
    Every plan priced for one business, as it would be billed: a further
    location of a brand pays the additional-location price a month (the
    annual price follows from it), and a location whose brand's setup fee
    another location carries pays no setup fee. The flags say which of
    the two applies, so the cabinet can explain the price.
    """

    business_id: BusinessId
    is_additional_location: IsAdditionalLocation = False
    is_setup_fee_covered: IsBrandSetupFeeCovered = False
