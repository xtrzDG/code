"""What the platform asks a carrier and the voice platform about numbers."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.phone_numbers import PhoneNumberProvider, PhoneNumberType
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
)
from app.schemas.typings.telephony.constrained_integers import PhoneNumberOfferCount
from app.schemas.typings.telephony.constrained_strings import (
    PhoneNumberCityQuery,
    PhoneNumberLabel,
)
from app.schemas.typings.telephony.strings import (
    PhoneNumberLocality,
    PhoneNumberRegion,
    ProviderPhoneNumberId,
    VoicePlatformPhoneNumberId,
)


class PhoneNumberSearchQuery(ImmutableDTO):
    """
    Numbers to offer in a country, of one kind, near a city when one is
    given; only numbers that take calls and need no papers to rent.
    """

    country_code: CountryCode
    number_type: PhoneNumberType
    city: PhoneNumberCityQuery | None = None
    limit: PhoneNumberOfferCount = PhoneNumberOfferCount(10)


class AvailablePhoneNumber(ImmutableDTO):
    """One number the carrier would rent now, and where it is from."""

    phone_number: E164PhoneNumber
    locality: PhoneNumberLocality | None = None
    region: PhoneNumberRegion | None = None


class PhoneNumberSearchResult(ImmutableDTO):
    """
    The numbers found and the carrier's monthly price of the kind in that
    country (None when it publishes none: such numbers are not offered).
    """

    numbers: list[AvailablePhoneNumber] = Field(
        default_factory=list[AvailablePhoneNumber]
    )
    monthly_cost_micro_usd: CostMicroUsd | None = None


class PhoneNumberPurchase(ImmutableDTO):
    """Rent exactly this number; the label names its business at the carrier."""

    phone_number: E164PhoneNumber
    label: PhoneNumberLabel


class ProvisionedPhoneNumber(ImmutableDTO):
    """A number the carrier rented to the platform."""

    provider: PhoneNumberProvider
    provider_number_id: ProviderPhoneNumberId
    phone_number: E164PhoneNumber


class VoicePlatformImport(ImmutableDTO):
    """
    Bring a rented number into the voice platform, answering with the
    business's agent when it has one (None: imported now, assigned later).
    """

    phone_number: E164PhoneNumber
    label: PhoneNumberLabel
    agent_id: VoiceAgentId | None = None


class PhoneNumberRelease(ImmutableDTO):
    """
    Give a number back: remove it from the voice platform (when it was
    imported), then return it to the carrier.
    """

    provider_number_id: ProviderPhoneNumberId
    voice_platform_number_id: VoicePlatformPhoneNumberId | None = None
