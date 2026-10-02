"""Who gets the owner's notifications: manager contacts and their addresses."""

import re

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.registries import LanguageRegistryContract
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.dto.businesses import ManagerContactInput
from app.schemas.dto.localization import PhoneNumberDetails
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.handoffs.strings import ManagerContactAddress
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.utilities.security.email_addresses import parse_email_address

MAX_MANAGER_CONTACTS: int = 20
MAX_MANAGER_NAME_LENGTH: int = 100

# Telegram chat ids are integers; group and channel chats are negative.
TELEGRAM_CHAT_ID_PATTERN: re.Pattern[str] = re.compile(r"^-?[0-9]{1,20}$")


def limit_manager_contacts(
    contact_inputs: list[ManagerContactInput],
) -> list[ManagerContactInput]:
    if len(contact_inputs) > MAX_MANAGER_CONTACTS:
        raise ValidationFailedError(
            f"A business can have at most {MAX_MANAGER_CONTACTS} manager contacts."
        )

    return contact_inputs


def validate_manager_contact(
    language_registry: LanguageRegistryContract,
    phone_number_parser: PhoneNumberParserContract,
    contact_input: ManagerContactInput,
    business: BusinessDocument,
) -> ManagerContact:
    if contact_input.name.strip() == "":
        raise ValidationFailedError("Manager name must not be empty.")

    if len(contact_input.name) > MAX_MANAGER_NAME_LENGTH:
        raise ValidationFailedError(
            f"Manager name must be at most {MAX_MANAGER_NAME_LENGTH} characters."
        )

    language: LanguageTag = contact_input.language or business.owner_language
    language_registry.get(language)
    return ManagerContact(
        name=contact_input.name,
        channel=contact_input.channel,
        address=validate_contact_address(phone_number_parser, contact_input, business),
        language=language,
    )


def validate_contact_address(
    phone_number_parser: PhoneNumberParserContract,
    contact_input: ManagerContactInput,
    business: BusinessDocument,
) -> ManagerContactAddress:
    match contact_input.channel:
        case ManagerContactChannel.TELEGRAM:
            chat_id: str = contact_input.address.strip()
            if TELEGRAM_CHAT_ID_PATTERN.fullmatch(chat_id) is None:
                raise ValidationFailedError(
                    "A Telegram contact needs the numeric chat id the platform "
                    "bot shows after the manager presses Start."
                )

            return ManagerContactAddress(chat_id)
        case ManagerContactChannel.EMAIL:
            email: EmailAddress = parse_email_address(contact_input.address)
            return ManagerContactAddress(str(email))
        case ManagerContactChannel.WHATSAPP | ManagerContactChannel.SMS:
            phone_number: PhoneNumberDetails = phone_number_parser.parse(
                RawPhoneNumberInput(str(contact_input.address)),
                business.country_code,
            )
            return ManagerContactAddress(str(phone_number.e164))
