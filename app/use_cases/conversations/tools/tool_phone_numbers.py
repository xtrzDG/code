"""Phone numbers a tool call names: parsed, or refused when not proved."""

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.schemas.dto.assistant_tools import AssistantToolContext
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.localization.strings import RawPhoneNumberInput


def require_verified_phone(
    phone_number_parser: PhoneNumberParserContract,
    raw_phone_number: RawPhoneNumberInput | None,
    context: AssistantToolContext,
) -> E164PhoneNumber | None:
    """
    The phone the channel proved for this customer. A different phone
    the model passes on is refused: it would let anyone manage someone
    else's bookings just by typing their number.

    Raises:
        AccessDeniedError: the model passed another phone.
        InvalidPhoneNumberError: the model passed something that is not
            a phone number of any country.
    """

    if raw_phone_number is None or str(raw_phone_number).strip() == "":
        return context.verified_phone_number

    claimed: E164PhoneNumber = phone_number_parser.parse(
        raw_phone_number,
        context.business_country_code,
    ).e164
    if claimed != context.verified_phone_number:
        raise AccessDeniedError(
            "This phone number is not confirmed for this conversation, so "
            "its bookings cannot be changed from here. Only bookings made "
            "in this conversation, or under the number the customer is "
            "writing or calling from, can be cancelled or moved; otherwise "
            "offer to pass the request to a colleague."
        )

    return claimed


def resolve_phone(
    phone_number_parser: PhoneNumberParserContract,
    raw_phone_number: RawPhoneNumberInput | None,
    context: AssistantToolContext,
) -> E164PhoneNumber | None:
    """
    Phone from the model in E.164, read with the business country for
    national formats; the contact's phone when the model gives none.

    Raises:
        InvalidPhoneNumberError: the model passed something that is not
            a phone number of any country.
    """

    if raw_phone_number is None or str(raw_phone_number).strip() == "":
        return context.contact_phone_number

    return phone_number_parser.parse(
        raw_phone_number,
        context.business_country_code,
    ).e164
