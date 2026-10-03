"""Connect the assistant's phone line."""

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.channels.channel_settings import ConnectChannelRequest
from app.schemas.dto.localization import PhoneNumberDetails
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.channels.strings import ChannelExternalId
from app.use_cases.channels.connection.channel_connection import (
    AccountCheck,
    ChannelConnection,
)


def connect_phone(
    phone_number_parser: PhoneNumberParserContract,
    require_free_account: AccountCheck,
    business: BusinessDocument,
    request: ConnectChannelRequest,
) -> ChannelConnection:
    if request.phone_number is None:
        raise ValidationFailedError("phone_number of the assistant line is required.")

    details: PhoneNumberDetails = phone_number_parser.parse(
        request.phone_number,
        request.country_hint or business.country_code,
    )
    external_id = ChannelExternalId(str(details.e164))
    require_free_account(ChannelKind.PHONE, external_id)
    return ChannelConnection(external_id=external_id, secret=None)
