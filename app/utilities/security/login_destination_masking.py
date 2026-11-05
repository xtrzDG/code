"""Hide most of a phone number or e-mail before showing or logging it."""

from app.schemas.dto.localization import PhoneNumberDetails
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.strings import MaskedLoginDestination

MASK_CHARACTER: str = "*"
VISIBLE_TRAILING_PHONE_DIGITS: int = 2
MASKED_EMAIL_LOCAL_PART: str = "***"


def mask_phone_number(phone_number: PhoneNumberDetails) -> MaskedLoginDestination:
    """
    Keep the "+<calling code>" prefix, the grouping and the last two digits.

    Example: "+995 555 12 34 56" becomes "+995 *** ** ** 56".
    """

    international_format: str = str(phone_number.international_format)
    calling_code_prefix: str = f"+{int(phone_number.calling_code)}"
    if not international_format.startswith(calling_code_prefix):
        return mask_e164_phone_number(phone_number.e164)

    national_part: str = international_format[len(calling_code_prefix) :]
    return MaskedLoginDestination(
        calling_code_prefix + mask_digits_except_trailing(national_part)
    )


def mask_e164_phone_number(phone_number: E164PhoneNumber) -> MaskedLoginDestination:
    """Keep "+" and the last two digits, e.g. "+**********56"."""

    return MaskedLoginDestination(mask_digits_except_trailing(str(phone_number)))


def mask_email_address(email: EmailAddress) -> MaskedLoginDestination:
    """
    Keep the first (and for longer names the last) letter and the domain.

    Example: "owner@example.com" becomes "o***r@example.com".
    """

    local_part, domain = str(email).rsplit("@", 1)
    last_visible_character: str = local_part[-1] if len(local_part) > 2 else ""
    return MaskedLoginDestination(
        f"{local_part[0]}{MASKED_EMAIL_LOCAL_PART}{last_visible_character}@{domain}"
    )


def mask_digits_except_trailing(text: str) -> str:
    digit_count: int = sum(1 for character in text if character.isdigit())
    first_visible_digit_index: int = digit_count - VISIBLE_TRAILING_PHONE_DIGITS
    masked_characters: list[str] = []
    digit_index: int = 0
    for character in text:
        if not character.isdigit():
            masked_characters.append(character)
            continue

        masked_characters.append(
            character if digit_index >= first_visible_digit_index else MASK_CHARACTER
        )
        digit_index += 1

    return "".join(masked_characters)
