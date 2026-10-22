"""
The cabinet's phone line: a number the platform rents for the business,
the numbers on offer and a request for one the team arranges by hand.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.phone_numbers import (
    PhoneNumberAvailability,
    PhoneNumberRequestStatus,
    PhoneNumberStatus,
    PhoneNumberType,
)
from app.schemas.dto.billing import Money
from app.schemas.dto.catalog.plan_quotes import QuotedMoney
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.localization.strings import FormattedPhoneNumber
from app.schemas.typings.telephony.booleans import (
    ArePhoneNumbersSelfServe,
    IsPhoneNumberAttached,
)
from app.schemas.typings.telephony.constrained_strings import PhoneNumberCityQuery
from app.schemas.typings.telephony.strings import (
    PhoneNumberLocality,
    PhoneNumberRegion,
)
from app.schemas.typings.users.prefixed_id import UserId


class PhoneLineQuery(ImmutableDTO):
    """A member reads the business's phone line; prices in `display_language`."""

    user_id: UserId
    business_id: BusinessId
    display_language: LanguageTag | None = None


class RentedPhoneNumberView(ImmutableDTO):
    """
    The number the platform rents for the business: where it is from, what
    it costs a month (fixed when it was taken), ACTIVE or RELEASING (being
    given back), and whether calls to it reach the voice agent yet
    (`is_attached`: false until the business has an agent, or for a few
    minutes after it was taken).
    """

    phone_number: E164PhoneNumber
    display_number: FormattedPhoneNumber
    country_code: CountryCode
    number_type: PhoneNumberType
    locality: PhoneNumberLocality | None = None
    monthly_price: QuotedMoney
    status: PhoneNumberStatus
    is_attached: IsPhoneNumberAttached
    rented_at: Microseconds


class PhoneNumberRequestView(ImmutableDTO):
    """The owner's request for a number the platform team arranges by hand."""

    country_code: CountryCode
    number_type: PhoneNumberType
    city: PhoneNumberCityQuery | None = None
    status: PhoneNumberRequestStatus
    requested_at: Microseconds


class PhoneLineView(ImmutableDTO):
    """
    The phone card: the rented number (None: the business rents none, its
    line is its own or not connected yet), an open request (None: none),
    whether this server rents numbers by itself
    (`are_numbers_self_serve`), the countries where an owner picks a number
    and has it at once (`self_serve_countries`; elsewhere the team arranges
    it), and the country the card starts with (the business's).
    """

    business_id: BusinessId
    rented_number: RentedPhoneNumberView | None = None
    open_request: PhoneNumberRequestView | None = None
    are_numbers_self_serve: ArePhoneNumbersSelfServe
    self_serve_countries: list[CountryCode] = Field(default_factory=list[CountryCode])
    default_country_code: CountryCode


class PhoneNumberOfferQuery(ImmutableDTO):
    """An owner looks for a number: country, kind and, optionally, a city."""

    user_id: UserId
    business_id: BusinessId
    country_code: CountryCode
    number_type: PhoneNumberType
    city: PhoneNumberCityQuery | None = None
    display_language: LanguageTag | None = None


class PhoneNumberOfferView(ImmutableDTO):
    """One number the owner may take now."""

    phone_number: E164PhoneNumber
    display_number: FormattedPhoneNumber
    locality: PhoneNumberLocality | None = None
    region: PhoneNumberRegion | None = None


class PhoneNumberOfferList(ImmutableDTO):
    """
    What a search found. SELF_SERVE: `offers` (possibly none near that
    city) at `monthly_price`, the owner's price of any of them.
    REQUIRES_DOCUMENTS or ON_REQUEST: no offers; the owner asks the team.
    """

    country_code: CountryCode
    number_type: PhoneNumberType
    availability: PhoneNumberAvailability
    monthly_price: QuotedMoney | None = None
    offers: list[PhoneNumberOfferView] = Field(
        default_factory=list[PhoneNumberOfferView]
    )


class RentPhoneNumberRequest(ImmutableDTO):
    """
    The number the owner chose, its kind, and the monthly price the cabinet
    showed (the purchase is refused when the price changed meanwhile).
    """

    phone_number: E164PhoneNumber
    number_type: PhoneNumberType
    monthly_price: Money


class RentPhoneNumberCommand(ImmutableDTO):
    """An owner takes a number for the business's phone line."""

    user_id: UserId
    business_id: BusinessId
    request: RentPhoneNumberRequest
    client_ip_address: ClientIpAddress | None = None
    display_language: LanguageTag | None = None


class PhoneNumberRequestBody(ImmutableDTO):
    """Where the owner would like a number the team arranges by hand."""

    country_code: CountryCode
    number_type: PhoneNumberType
    city: PhoneNumberCityQuery | None = None


class RequestPhoneNumberCommand(ImmutableDTO):
    """An owner asks the platform team for a number."""

    user_id: UserId
    business_id: BusinessId
    request: PhoneNumberRequestBody
    client_ip_address: ClientIpAddress | None = None


class CancelPhoneNumberRequestCommand(ImmutableDTO):
    """An owner no longer needs the number they asked the team for."""

    user_id: UserId
    business_id: BusinessId
    client_ip_address: ClientIpAddress | None = None
