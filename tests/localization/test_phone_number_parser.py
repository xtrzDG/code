import pytest

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.schemas.constants.localization import PhoneNumberKind
from app.schemas.dto.localization import PhoneNumberDetails
from app.schemas.exceptions.application_errors import (
    InvalidPhoneNumberError,
    ValidationFailedError,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    TimezoneName,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.utilities.localization.phone_number_parser import PhoneNumberParser

PARSER: PhoneNumberParserContract = PhoneNumberParser()


def parse(raw_phone_number: str, country_hint: str | None = None) -> PhoneNumberDetails:
    return PARSER.parse(
        RawPhoneNumberInput(raw_phone_number),
        CountryCode(country_hint) if country_hint is not None else None,
    )


@pytest.mark.parametrize(
    ("raw_phone_number", "country_hint", "expected_e164", "expected_country"),
    [
        # Georgia: international, "00" prefix, national mobile and Tbilisi line.
        ("+995 555 12-34-56", None, "+995555123456", "GE"),
        ("00 995 555 12 34 56", None, "+995555123456", "GE"),
        ("00995555123456", "GE", "+995555123456", "GE"),
        ("555 12 34 56", "GE", "+995555123456", "GE"),
        ("032 2 12 34 56", "GE", "+995322123456", "GE"),
        # Armenia.
        ("+374 77 123456", None, "+37477123456", "AM"),
        ("077 123456", "AM", "+37477123456", "AM"),
        # Israel.
        ("+972 50-234-5678", None, "+972502345678", "IL"),
        ("050-234-5678", "IL", "+972502345678", "IL"),
        ("02-123-4567", "IL", "+97221234567", "IL"),
        # Kazakhstan shares +7 with Russia; the prefix decides the country.
        ("+7 771 000 9998", None, "+77710009998", "KZ"),
        ("8 771 000 9998", "KZ", "+77710009998", "KZ"),
        ("8 (999) 123-45-67", "RU", "+79991234567", "RU"),
        # Poland and Lithuania.
        ("+48 512 345 678", None, "+48512345678", "PL"),
        ("12 345 67 89", "PL", "+48123456789", "PL"),
        ("+370 612 34567", None, "+37061234567", "LT"),
        ("8 612 34567", "LT", "+37061234567", "LT"),
        # USA and the UK.
        ("(201) 555-0123", "US", "+12015550123", "US"),
        ("+1 212 555 0123", None, "+12125550123", "US"),
        ("tel:+1-212-555-0123", None, "+12125550123", "US"),
        ("020 7946 0018", "GB", "+442079460018", "GB"),
        ("07400 123456", "GB", "+447400123456", "GB"),
        # Brazil, India, Germany, UAE, Japan.
        ("+55 11 96123-4567", None, "+5511961234567", "BR"),
        ("(11) 2345-6789", "BR", "+551123456789", "BR"),
        ("+91 81234 56789", None, "+918123456789", "IN"),
        ("081234 56789", "IN", "+918123456789", "IN"),
        ("030 123456", "DE", "+4930123456", "DE"),
        ("+49 1512 3456789", None, "+4915123456789", "DE"),
        ("050 123 4567", "AE", "+971501234567", "AE"),
        ("+971 2 234 5678", None, "+97122345678", "AE"),
        ("090-1234-5678", "JP", "+819012345678", "JP"),
        ("+81 3-1234-5678", None, "+81312345678", "JP"),
    ],
)
def test_numbers_of_many_countries_become_e164(
    raw_phone_number: str,
    country_hint: str | None,
    expected_e164: str,
    expected_country: str,
) -> None:
    details = parse(raw_phone_number, country_hint)

    assert details.e164 == expected_e164
    assert type(details.e164) is E164PhoneNumber
    assert details.country_code == expected_country
    assert type(details.country_code) is CountryCode
    assert expected_e164.startswith(f"+{int(details.calling_code)}")


def test_international_prefix_00_is_read_as_plus_even_with_another_hint() -> None:
    # The USA dials 011 abroad, so "00" is not its international prefix.
    details = parse("00 995 555 12 34 56", "US")

    assert details.e164 == "+995555123456"
    assert details.country_code == "GE"


def test_international_number_wins_over_a_different_hint() -> None:
    details = parse("+972 50-234-5678", "GE")

    assert details.country_code == "IL"


def test_non_latin_digits_and_full_width_plus_are_accepted() -> None:
    arabic_indic = parse("+٩٩٥ ٥٥٥ ١٢٣ ٤٥٦")
    full_width_plus = parse("＋995 555 123 456")

    assert arabic_indic.e164 == "+995555123456"
    assert full_width_plus.e164 == "+995555123456"


def test_formats_and_calling_code() -> None:
    details = parse("8 (999) 123-45-67", "RU")

    assert details.international_format == "+7 999 123-45-67"
    assert details.national_format == "8 (999) 123-45-67"
    assert details.calling_code == 7


@pytest.mark.parametrize(
    ("raw_phone_number", "country_hint", "expected_kind", "expected_is_mobile"),
    [
        ("+995 555 12 34 56", None, PhoneNumberKind.MOBILE, True),
        ("+995 32 212 34 56", None, PhoneNumberKind.FIXED_LINE, False),
        ("+1 212 555 0123", None, PhoneNumberKind.FIXED_LINE_OR_MOBILE, True),
        ("+1 800 555 0199", None, PhoneNumberKind.TOLL_FREE, False),
        ("+44 56 1234 5678", None, PhoneNumberKind.VOIP, False),
        ("+44 9012 345678", None, PhoneNumberKind.OTHER, False),
    ],
)
def test_line_kind_and_mobile_capability(
    raw_phone_number: str,
    country_hint: str | None,
    expected_kind: PhoneNumberKind,
    expected_is_mobile: bool,
) -> None:
    details = parse(raw_phone_number, country_hint)

    assert details.kind is expected_kind
    assert details.is_mobile is expected_is_mobile


def test_time_zones_are_narrowed_to_the_country() -> None:
    # libphonenumber lists every +7 zone for Kazakh mobiles.
    kazakh = parse("+7 771 000 9998")
    # libphonenumber maps Lithuanian mobiles to Europe/Bucharest (same offset).
    lithuanian = parse("+370 612 34567")
    georgian = parse("+995 555 12 34 56")
    russian = parse("+7 999 123 45 67")

    assert all(str(zone).startswith("Asia/") for zone in kazakh.timezones)
    assert TimezoneName("Asia/Almaty") in kazakh.timezones
    assert lithuanian.timezones == [TimezoneName("Europe/Vilnius")]
    assert georgian.timezones == [TimezoneName("Asia/Tbilisi")]
    assert TimezoneName("Europe/Moscow") in russian.timezones
    assert TimezoneName("Asia/Almaty") not in russian.timezones
    assert len(russian.timezones) > 10


def test_regions_unknown_to_cldr_keep_libphonenumber_zones() -> None:
    kosovo = parse("+383 44 123 456")

    assert kosovo.country_code == "XK"
    assert kosovo.timezones == [TimezoneName("Europe/Belgrade")]
    assert all(str(zone) != "Etc/Unknown" for zone in kosovo.timezones)


@pytest.mark.parametrize(
    ("raw_phone_number", "country_hint"),
    [
        ("+995 555", None),
        ("+972 50-123-4567", None),
        ("hello", None),
        ("555 12 34 56", None),
        ("12345", "DE"),
        ("+1 999 555 0123", None),
        ("", None),
        ("   ", "GE"),
        ("+800 1234 5678", None),
        ("+882 3456 7890", None),
    ],
)
def test_invalid_and_non_geographic_numbers_are_rejected(
    raw_phone_number: str,
    country_hint: str | None,
) -> None:
    with pytest.raises(InvalidPhoneNumberError):
        parse(raw_phone_number, country_hint)


def test_invalid_number_error_is_a_validation_error_and_never_echoes_input() -> None:
    secret_looking_input = "+995 555 SECRET-TOKEN 9999"
    with pytest.raises(ValidationFailedError) as error_info:
        parse(secret_looking_input)

    assert "SECRET" not in str(error_info.value)


def test_very_long_input_is_rejected_without_parsing() -> None:
    long_input = "+995 555 12 34 56 " + "9" * 500
    with pytest.raises(InvalidPhoneNumberError) as error_info:
        parse(long_input)

    assert "9999" not in str(error_info.value)


def test_unknown_hint_is_ignored_for_international_numbers() -> None:
    # "ZZ" is shaped like a country code but has no numbering plan.
    details = parse("+995 555 12 34 56", "ZZ")

    assert details.country_code == "GE"
    with pytest.raises(InvalidPhoneNumberError):
        parse("555 12 34 56", "ZZ")
