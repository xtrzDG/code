"""Numbers the platform rents for businesses (W21, migration 1213)."""

from base_pydantic_schemas import BaseDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.phone_numbers import (
    PhoneNumberProvider,
    PhoneNumberReleaseReason,
    PhoneNumberRequestStatus,
    PhoneNumberStatus,
    PhoneNumberType,
)
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
)
from app.schemas.typings.telephony.constrained_integers import PhoneNumberRentalMinor
from app.schemas.typings.telephony.constrained_strings import (
    PhoneNumberCityQuery,
    RentedLineNumber,
    VoiceFallbackUrl,
)
from app.schemas.typings.telephony.prefixed_id import (
    PhoneNumberId,
    PhoneNumberRequestId,
)
from app.schemas.typings.telephony.strings import (
    PhoneNumberLocality,
    ProviderPhoneNumberId,
    VoicePlatformPhoneNumberId,
)
from app.schemas.typings.users.prefixed_id import UserId


class PhoneNumberDocument(BaseDocument):
    """
    A number the platform rented for a business from a carrier and imported
    into the voice platform, so calls to it reach the business's voice
    agent. The business's phone channel carries the same number (its
    `external_id`), which is how a call finds its business.

    The owner's price (`monthly_price_minor` in `currency_code`) and the
    carrier's (`monthly_cost_micro_usd`) are fixed when the number is
    taken. Rental months run from `rented_at`, month by month in the
    business's time zone; `billed_until` is where the next month begins,
    moved by the rental job once that month is billed, included or the
    number released (bill_phone_number_rentals).

    `voice_platform_number_id` is set once the voice platform imported the
    number and `attached_agent_id` names the agent it answers with (None
    until the business has one); `voice_fallback_url` is the call fallback
    the carrier has for it (version 2); the maintenance job keeps all three
    in step.
    Giving a number up makes it RELEASING (`release_reason`, `release_requested_at`);
    the maintenance job returns it to the voice platform and the carrier,
    then it is RELEASED (`released_at`) and stays as the record.
    """

    id: PhoneNumberId = Field(default_factory=PhoneNumberId)
    business_id: BusinessId
    provider: PhoneNumberProvider
    provider_number_id: ProviderPhoneNumberId
    phone_number: RentedLineNumber
    country_code: CountryCode
    number_type: PhoneNumberType
    locality: PhoneNumberLocality | None = None
    monthly_price_minor: PhoneNumberRentalMinor
    currency_code: CurrencyCode
    monthly_cost_micro_usd: CostMicroUsd
    status: PhoneNumberStatus = PhoneNumberStatus.ACTIVE
    voice_platform_number_id: VoicePlatformPhoneNumberId | None = None
    attached_agent_id: VoiceAgentId | None = None
    rented_by: UserId
    rented_at: Microseconds
    billed_until: Microseconds
    release_reason: PhoneNumberReleaseReason | None = None
    release_requested_at: Microseconds | None = None
    released_at: Microseconds | None = None
    voice_fallback_url: VoiceFallbackUrl | None = None
    schema_version: SchemaVersion = SchemaVersion("2")


class PhoneNumberRequestDocument(BaseDocument):
    """
    An owner asked the platform team for a number it arranges by hand: in a
    country whose regulator wants the business's documents, or where this
    server rents none by itself. One per business (the id derives from it):
    asking again after it was done or cancelled opens it again. The team
    gets an e-mail; the request is DONE once the business's phone channel
    is connected (the maintenance job notices), or CANCELLED by the owner.
    """

    id: PhoneNumberRequestId
    business_id: BusinessId
    requested_by: UserId
    country_code: CountryCode
    number_type: PhoneNumberType
    city: PhoneNumberCityQuery | None = None
    status: PhoneNumberRequestStatus = PhoneNumberRequestStatus.OPEN
    requested_at: Microseconds
    closed_at: Microseconds | None = None
