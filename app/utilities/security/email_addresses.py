"""Normalization of e-mail addresses typed by people of any country."""

from base_typed_string import BaseTypedStringError

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.strings import RawManagerContactAddress
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.strings import RawEmailAddressInput


def parse_email_address(
    raw_email: RawEmailAddressInput | RawManagerContactAddress,
) -> EmailAddress:
    """
    Trim and lower-case an address; internationalized domains such as
    "пример.рф" are stored in their ASCII (punycode) form.

    Raises:
        ValidationFailedError: not an e-mail address.
    """

    trimmed_email: str = str(raw_email).strip().lower()
    local_part, separator, domain = trimmed_email.rpartition("@")
    if separator == "" or local_part == "" or domain == "":
        raise ValidationFailedError("Enter a valid e-mail address.")

    try:
        ascii_domain: str = domain.encode("idna").decode("ascii")
        return EmailAddress(f"{local_part}@{ascii_domain}")
    except (UnicodeError, BaseTypedStringError) as error:
        raise ValidationFailedError("Enter a valid e-mail address.") from error
