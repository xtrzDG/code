"""
The person behind a team invitation by phone number or e-mail, shared by
a business's team and a brand's: an existing account is reused unchanged,
anyone else gets an unverified one they confirm by signing in with a code.
"""

from typed_time_provider import Microseconds

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.users import UserDocument
from app.schemas.dto.localization import PhoneNumberDetails
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.strings import RawEmailAddressInput, UserDisplayName
from app.utilities.security.email_addresses import parse_email_address

MAX_DISPLAY_NAME_LENGTH: int = 100


def clean_display_name(display_name: UserDisplayName | None) -> UserDisplayName | None:
    """
    The invited person's name as typed (None when blank).

    Raises:
        ValidationFailedError: longer than MAX_DISPLAY_NAME_LENGTH.
    """

    if display_name is None:
        return None

    if len(display_name) > MAX_DISPLAY_NAME_LENGTH:
        raise ValidationFailedError(
            f"Display name must be at most {MAX_DISPLAY_NAME_LENGTH} characters."
        )

    return None if display_name.strip() == "" else display_name


def find_or_create_invited_user(
    user_repo: UserRepoContract,
    phone_number_parser: PhoneNumberParserContract,
    phone_number: RawPhoneNumberInput | None,
    email: RawEmailAddressInput | None,
    country: CountryCode,
    locale: LanguageTag,
    display_name: UserDisplayName | None,
    now: Microseconds,
) -> UserDocument:
    """
    The account of the phone number (read in `country` when national) or
    e-mail; exactly one of them is given.

    Raises:
        ValidationFailedError: neither or both are given, or one is invalid.
    """

    if phone_number is not None and email is None:
        parsed: PhoneNumberDetails = phone_number_parser.parse(phone_number, country)
        existing: UserDocument | None = user_repo.find_by_phone_number(parsed.e164)
        if existing is not None:
            return existing

        created = UserDocument(
            login_method=LoginMethod.PHONE,
            phone_number=parsed.e164,
            country_code=parsed.country_code,
            locale=locale,
            display_name=display_name,
            created_at=now,
            updated_at=now,
        )
        user_repo.save(created)
        return created

    if email is not None and phone_number is None:
        address: EmailAddress = parse_email_address(email)
        existing_by_email: UserDocument | None = user_repo.find_by_email(address)
        if existing_by_email is not None:
            return existing_by_email

        created_by_email = UserDocument(
            login_method=LoginMethod.EMAIL,
            email=address,
            locale=locale,
            display_name=display_name,
            created_at=now,
            updated_at=now,
        )
        user_repo.save(created_by_email)
        return created_by_email

    raise ValidationFailedError("Enter either a phone number or an e-mail.")
