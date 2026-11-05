import phonenumbers
from phonenumbers import (
    NumberParseException,
    PhoneNumber,
    PhoneNumberFormat,
    PhoneNumberType,
)
from phonenumbers.timezone import time_zones_for_number

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.schemas.constants.localization import PhoneNumberKind
from app.schemas.dto.localization import PhoneNumberDetails
from app.schemas.exceptions.application_errors import InvalidPhoneNumberError
from app.schemas.typings.localization.constrained_integers import CountryCallingCode
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    TimezoneName,
)
from app.schemas.typings.localization.strings import (
    FormattedPhoneNumber,
    RawPhoneNumberInput,
)
from app.utilities.localization.timezones import (
    is_known_timezone_name,
    list_territory_timezone_names,
)

# Longer input is never a phone number; it is rejected without being parsed.
MAX_RAW_PHONE_NUMBER_LENGTH: int = 64
INTERNATIONAL_CALL_PREFIX: str = "00"
PLUS_SIGN: str = "+"
LEADING_FORMATTING_CHARACTERS: str = " \t\n\r()-./ "
NON_GEOGRAPHIC_REGION_CODE: str = "001"
UNKNOWN_TIMEZONE_NAME: str = "Etc/Unknown"
INVALID_NUMBER_MESSAGE: str = (
    "This is not a valid phone number. Type it with the country code, "
    "for example +995 555 12 34 56, or choose the country."
)
PHONE_NUMBER_KINDS: dict[int, PhoneNumberKind] = {
    PhoneNumberType.MOBILE: PhoneNumberKind.MOBILE,
    PhoneNumberType.FIXED_LINE: PhoneNumberKind.FIXED_LINE,
    PhoneNumberType.FIXED_LINE_OR_MOBILE: PhoneNumberKind.FIXED_LINE_OR_MOBILE,
    PhoneNumberType.TOLL_FREE: PhoneNumberKind.TOLL_FREE,
    PhoneNumberType.VOIP: PhoneNumberKind.VOIP,
}
# Kinds that may receive SMS and messenger codes. Numbering plans of the
# USA, Canada and some other countries cannot tell mobile from fixed lines.
MOBILE_CAPABLE_KINDS: frozenset[PhoneNumberKind] = frozenset(
    {PhoneNumberKind.MOBILE, PhoneNumberKind.FIXED_LINE_OR_MOBILE}
)


class PhoneNumberParser(PhoneNumberParserContract):
    """
    Parse a phone number of any country with libphonenumber metadata.

    Accepts international ("+995 555 12-34-56", "00 995 ...", "tel:+1-..."),
    national with a country hint ("8 (999) 123-45-67" + RU, "020 7946 0018" +
    GB) and non-Latin digits. Only numbers valid in the numbering plan of a
    country are accepted; non-geographic numbers (+800, +882, ...) are
    rejected because a business and its customers live in a country. Error
    messages never repeat the input.
    """

    def parse(
        self,
        raw_phone_number: RawPhoneNumberInput,
        country_hint: CountryCode | None,
    ) -> PhoneNumberDetails:
        trimmed_input: str = str(raw_phone_number).strip()
        if trimmed_input == "" or len(trimmed_input) > MAX_RAW_PHONE_NUMBER_LENGTH:
            raise InvalidPhoneNumberError(INVALID_NUMBER_MESSAGE)

        region_hint: str | None = None
        if (
            country_hint is not None
            and str(country_hint) in phonenumbers.SUPPORTED_REGIONS
        ):
            region_hint = str(country_hint)

        phone_number: PhoneNumber = find_valid_number(trimmed_input, region_hint)
        region_code: str | None = phonenumbers.region_code_for_number(phone_number)
        if (
            region_code is None
            or region_code == NON_GEOGRAPHIC_REGION_CODE
            or region_code not in phonenumbers.SUPPORTED_REGIONS
            or phone_number.country_code is None
        ):
            raise InvalidPhoneNumberError(INVALID_NUMBER_MESSAGE)

        kind: PhoneNumberKind = PHONE_NUMBER_KINDS.get(
            phonenumbers.number_type(phone_number),
            PhoneNumberKind.OTHER,
        )
        try:
            e164: E164PhoneNumber = E164PhoneNumber(
                phonenumbers.format_number(phone_number, PhoneNumberFormat.E164)
            )
        except ValueError as error:
            raise InvalidPhoneNumberError(INVALID_NUMBER_MESSAGE) from error

        return PhoneNumberDetails(
            e164=e164,
            country_code=CountryCode(region_code),
            calling_code=CountryCallingCode(phone_number.country_code),
            kind=kind,
            is_mobile=kind in MOBILE_CAPABLE_KINDS,
            international_format=FormattedPhoneNumber(
                phonenumbers.format_number(
                    phone_number,
                    PhoneNumberFormat.INTERNATIONAL,
                )
            ),
            national_format=FormattedPhoneNumber(
                phonenumbers.format_number(phone_number, PhoneNumberFormat.NATIONAL)
            ),
            timezones=find_number_timezones(phone_number, region_code),
        )


def find_valid_number(trimmed_input: str, region_hint: str | None) -> PhoneNumber:
    """
    Try the input as typed, then with a leading "00" read as "+".

    "00" is the international call prefix in most of the world, but not in
    the hint country of every caller (the USA dials 011), so a number like
    "00 995 555 12 34 56" typed with hint US is retried as "+995 ...".
    """

    candidates: list[tuple[str, str | None]] = [(trimmed_input, region_hint)]
    unformatted_input: str = trimmed_input.lstrip(LEADING_FORMATTING_CHARACTERS)
    if unformatted_input.startswith(INTERNATIONAL_CALL_PREFIX):
        candidates.append(
            (PLUS_SIGN + unformatted_input[len(INTERNATIONAL_CALL_PREFIX) :], None)
        )

    for candidate_input, candidate_region in candidates:
        try:
            phone_number: PhoneNumber = phonenumbers.parse(
                candidate_input,
                candidate_region,
            )
        except NumberParseException:
            continue

        if phonenumbers.is_valid_number(phone_number):
            return phone_number

    raise InvalidPhoneNumberError(INVALID_NUMBER_MESSAGE)


def find_number_timezones(
    phone_number: PhoneNumber,
    region_code: str,
) -> list[TimezoneName]:
    """
    Time zones of a number, narrowed to the time zones of its country.

    libphonenumber maps a prefix to every zone of its calling code (+7 lists
    Russia and Kazakhstan) and sometimes to a zone of another country with
    the same offset, so its answer is intersected with the CLDR zones of the
    number's country. Without an intersection the country zones are returned.
    """

    number_zone_names: list[str] = sorted(
        {
            zone_name
            for zone_name in time_zones_for_number(phone_number)
            if zone_name != UNKNOWN_TIMEZONE_NAME and is_known_timezone_name(zone_name)
        }
    )
    country_zone_names: list[TimezoneName] = list_territory_timezone_names(region_code)
    if country_zone_names == []:
        return [TimezoneName(zone_name) for zone_name in number_zone_names]

    matching_zone_names: list[TimezoneName] = [
        zone_name for zone_name in country_zone_names if zone_name in number_zone_names
    ]
    if matching_zone_names != []:
        return matching_zone_names

    return country_zone_names
