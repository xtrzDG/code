"""Connect the assistant's phone line."""

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.phone_numbers import PhoneNumberRepoContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.phone_numbers import PhoneNumberStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.phone_numbers import PhoneNumberDocument
from app.schemas.dto.channels.channel_settings import ConnectChannelRequest
from app.schemas.dto.localization import PhoneNumberDetails
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
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
    phone_number_repo: PhoneNumberRepoContract | None = None,
) -> ChannelConnection:
    """
    The assistant line as E.164. While the platform rents the business a
    number, the line is that number: another one is refused (ConflictError)
    until the rented number is given back.
    """

    if request.phone_number is None:
        raise ValidationFailedError("phone_number of the assistant line is required.")

    details: PhoneNumberDetails = phone_number_parser.parse(
        request.phone_number,
        request.country_hint or business.country_code,
    )
    external_id = ChannelExternalId(str(details.e164))
    rented: PhoneNumberDocument | None = (
        None if phone_number_repo is None else phone_number_repo.find_held(business.id)
    )
    if (
        rented is not None
        and rented.status is PhoneNumberStatus.ACTIVE
        and str(rented.phone_number) != str(details.e164)
    ):
        raise ConflictError(
            "The business rents a number from us for its phone line. Turn the "
            "phone channel off to give it back before connecting another number."
        )

    require_free_account(ChannelKind.PHONE, external_id)
    return ChannelConnection(external_id=external_id, secret=None)
