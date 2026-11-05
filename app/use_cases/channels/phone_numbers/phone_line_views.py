"""The phone card's views of a rented number, a request and an offer."""

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.schemas.constants.phone_numbers import PhoneNumberRequestStatus
from app.schemas.domain.phone_numbers import (
    PhoneNumberDocument,
    PhoneNumberRequestDocument,
)
from app.schemas.dto.billing import Money
from app.schemas.dto.phone_numbers.phone_line import (
    PhoneNumberOfferView,
    PhoneNumberRequestView,
    RentedPhoneNumberView,
)
from app.schemas.dto.phone_numbers.provisioning import AvailablePhoneNumber
from app.schemas.exceptions.application_errors import InvalidPhoneNumberError
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.localization.strings import (
    FormattedPhoneNumber,
    RawPhoneNumberInput,
)
from app.schemas.typings.telephony.booleans import HasAnsweringVoiceAgent
from app.schemas.typings.telephony.constrained_strings import (
    PhoneNumberOfferToken,
    RentedLineNumber,
)
from app.use_cases.shared.subscription_pricing import quote_money


def display_number(
    phone_number_parser: PhoneNumberParserContract,
    phone_number: E164PhoneNumber | RentedLineNumber,
) -> FormattedPhoneNumber:
    """ "+1 512-555-0142"; the number itself when no numbering plan knows it."""

    try:
        return phone_number_parser.parse(
            RawPhoneNumberInput(str(phone_number)), None
        ).international_format
    except InvalidPhoneNumberError:
        return FormattedPhoneNumber(str(phone_number))


def rental_price(number: PhoneNumberDocument) -> Money:
    """A rented number's monthly price as money."""

    return Money(
        amount_minor=MoneyAmountMinor(int(number.monthly_price_minor)),
        currency_code=number.currency_code,
    )


def build_rented_number_view(
    number: PhoneNumberDocument,
    phone_number_parser: PhoneNumberParserContract,
    language: LanguageTag,
    has_answering_agent: HasAnsweringVoiceAgent,
) -> RentedPhoneNumberView:
    return RentedPhoneNumberView(
        phone_number=number.phone_number,
        display_number=display_number(phone_number_parser, number.phone_number),
        country_code=number.country_code,
        number_type=number.number_type,
        locality=number.locality,
        monthly_price=quote_money(rental_price(number), False, language),
        status=number.status,
        is_attached=number.attached_agent_id is not None
        and number.voice_platform_number_id is not None,
        has_answering_agent=has_answering_agent,
        rented_at=number.rented_at,
    )


def build_open_request_view(
    request: PhoneNumberRequestDocument | None,
) -> PhoneNumberRequestView | None:
    """The request while it is open; None otherwise."""

    if request is None or request.status is not PhoneNumberRequestStatus.OPEN:
        return None

    return PhoneNumberRequestView(
        country_code=request.country_code,
        number_type=request.number_type,
        city=request.city,
        status=request.status,
        requested_at=request.requested_at,
    )


def build_offer_view(
    offer: AvailablePhoneNumber,
    phone_number_parser: PhoneNumberParserContract,
    offer_token: PhoneNumberOfferToken,
) -> PhoneNumberOfferView:
    return PhoneNumberOfferView(
        phone_number=offer.phone_number,
        display_number=display_number(phone_number_parser, offer.phone_number),
        offer_token=offer_token,
        locality=offer.locality,
        region=offer.region,
    )
