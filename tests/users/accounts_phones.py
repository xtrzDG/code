"""Example phone numbers and a parser over the real `phonenumbers` plans."""

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat, PhoneNumberType
from phonenumbers import timezone as phone_timezones

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

# Example mobile numbers (valid in their numbering plans) per country.
GEORGIA_MOBILE: str = "+995 555 12 34 56"
USA_MOBILE: str = "+1 201-555-0123"
BRAZIL_MOBILE: str = "+55 11 96123-4567"
INDIA_MOBILE: str = "+91 81234 56789"
GERMANY_MOBILE: str = "+49 1512 3456789"
ISRAEL_MOBILE: str = "+972 50-234-5678"
UAE_MOBILE: str = "+971 50 123 4567"
JAPAN_MOBILE: str = "+81 90-1234-5678"
NORTH_KOREA_MOBILE: str = "+850 192 123 4567"
IRAN_MOBILE: str = "+98 912 345 6789"
MONACO_MOBILE: str = "+377 6 12 34 56 78"


PHONE_NUMBER_KINDS: dict[int, PhoneNumberKind] = {
    PhoneNumberType.MOBILE: PhoneNumberKind.MOBILE,
    PhoneNumberType.FIXED_LINE: PhoneNumberKind.FIXED_LINE,
    PhoneNumberType.FIXED_LINE_OR_MOBILE: PhoneNumberKind.FIXED_LINE_OR_MOBILE,
    PhoneNumberType.TOLL_FREE: PhoneNumberKind.TOLL_FREE,
    PhoneNumberType.VOIP: PhoneNumberKind.VOIP,
}


class PhonenumbersParser(PhoneNumberParserContract):
    """Test parser over the real numbering plans of every country."""

    def parse(
        self,
        raw_phone_number: RawPhoneNumberInput,
        country_hint: CountryCode | None,
    ) -> PhoneNumberDetails:
        try:
            number = phonenumbers.parse(
                str(raw_phone_number),
                None if country_hint is None else str(country_hint),
            )
        except NumberParseException as error:
            raise InvalidPhoneNumberError("Not a phone number.") from error

        region: str | None = phonenumbers.region_code_for_number(number)
        if not phonenumbers.is_valid_number(number) or region is None:
            raise InvalidPhoneNumberError("Not a valid phone number.")

        kind: PhoneNumberKind = PHONE_NUMBER_KINDS.get(
            phonenumbers.number_type(number),
            PhoneNumberKind.OTHER,
        )
        return PhoneNumberDetails(
            e164=E164PhoneNumber(
                phonenumbers.format_number(number, PhoneNumberFormat.E164)
            ),
            country_code=CountryCode(region),
            calling_code=CountryCallingCode(number.country_code or 0),
            kind=kind,
            is_mobile=kind
            in (PhoneNumberKind.MOBILE, PhoneNumberKind.FIXED_LINE_OR_MOBILE),
            international_format=FormattedPhoneNumber(
                phonenumbers.format_number(number, PhoneNumberFormat.INTERNATIONAL)
            ),
            national_format=FormattedPhoneNumber(
                phonenumbers.format_number(number, PhoneNumberFormat.NATIONAL)
            ),
            timezones=[
                TimezoneName(zone)
                for zone in phone_timezones.time_zones_for_number(number)
                if zone != "Etc/Unknown"
            ],
        )
