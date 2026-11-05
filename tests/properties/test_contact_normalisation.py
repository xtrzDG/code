"""
Contact normalisation (SDLC-07): parsing a phone number or an e-mail
address is idempotent (the stored form parses to itself), and the ways
people type the same contact (spacing, dashes, the national form with its
country, "00" for "+", capitals, surrounding spaces, an international
domain) all store as one value.
"""

import phonenumbers
from hypothesis import given
from hypothesis import strategies as st
from phonenumbers import PhoneNumber, PhoneNumberFormat, PhoneNumberType

from app.schemas.dto.localization import PhoneNumberDetails
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.strings import RawEmailAddressInput
from app.utilities.localization.phone_number_parser import PhoneNumberParser
from app.utilities.security.email_addresses import parse_email_address

PARSER: PhoneNumberParser = PhoneNumberParser()
# The first market and the countries its businesses' customers call from.
REGIONS: tuple[str, ...] = ("IT", "DE", "FR", "ES", "GB", "GE", "US", "IL", "PL", "RO")
KINDS: tuple[int, ...] = (
    PhoneNumberType.MOBILE,
    PhoneNumberType.FIXED_LINE,
)
SEPARATORS: tuple[str, ...] = ("", " ", "-", ".")
LOCAL_CHARACTERS: str = (
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._%+-"
)


def example(region: str, kind: int) -> PhoneNumber:
    number = phonenumbers.example_number_for_type(region, kind)
    assert number is not None, (region, kind)
    return number


EXAMPLES: tuple[tuple[str, PhoneNumber], ...] = tuple(
    (region, example(region, kind)) for region in REGIONS for kind in KINDS
)


def parse(text: str, country: str | None) -> PhoneNumberDetails:
    hint = None if country is None else CountryCode(country)
    return PARSER.parse(RawPhoneNumberInput(text), hint)


@st.composite
def typed_numbers(draw: st.DrawFn) -> tuple[str, str | None, str]:
    """A number as a person types it, its country hint and its E.164 form."""

    region, number = draw(st.sampled_from(EXAMPLES))
    e164 = phonenumbers.format_number(number, PhoneNumberFormat.E164)
    style = draw(st.sampled_from(("e164", "international", "national", "00", "tel")))
    separator = draw(st.sampled_from(SEPARATORS))
    if style == "national":
        national = phonenumbers.format_number(number, PhoneNumberFormat.NATIONAL)
        return national.replace(" ", separator), region, e164
    if style == "tel":
        return phonenumbers.format_number(number, PhoneNumberFormat.RFC3966), None, e164
    spaced = phonenumbers.format_number(number, PhoneNumberFormat.INTERNATIONAL)
    typed = e164 if style == "e164" else spaced.replace(" ", separator)
    if style == "00":
        typed = "00" + typed.removeprefix("+")
    padding = draw(st.sampled_from(("", " ", "  ", "\t")))
    return padding + typed + padding, draw(st.none() | st.sampled_from(REGIONS)), e164


@given(typed_numbers())
def test_every_typed_form_of_a_number_stores_as_its_e164(
    typed: tuple[str, str | None, str],
) -> None:
    text, country, e164 = typed

    details = parse(text, country)

    assert str(details.e164) == e164


@given(typed_numbers(), st.none() | st.sampled_from(REGIONS))
def test_a_stored_number_parses_to_itself(
    typed: tuple[str, str | None, str], other_country: str | None
) -> None:
    text, country, _ = typed
    details = parse(text, country)

    again = parse(str(details.e164), other_country)
    from_international = parse(str(details.international_format), None)

    assert again == details
    assert from_international.e164 == details.e164


@st.composite
def typed_addresses(draw: st.DrawFn) -> str:
    local = draw(st.text(alphabet=LOCAL_CHARACTERS, min_size=1, max_size=20))
    labels = draw(
        st.lists(
            st.text(
                alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=12
            ),
            min_size=1,
            max_size=3,
        )
    )
    top = draw(st.sampled_from(("it", "com", "de", "ge", "co.uk", "рф", "москва")))
    domain = ".".join([*labels, top])
    if draw(st.booleans()):
        domain = domain.upper() if top.isascii() else domain
    padding = draw(st.sampled_from(("", " ", "\t", "  ")))
    return f"{padding}{local}@{domain}{padding}"


@given(typed_addresses())
def test_an_address_parses_to_itself_once_stored(typed: str) -> None:
    stored = parse_email_address(RawEmailAddressInput(typed))

    assert parse_email_address(RawEmailAddressInput(str(stored))) == stored
    assert str(stored) == str(stored).strip().lower()
    assert str(stored).isascii()


@given(typed_addresses(), st.sampled_from(("", " ", "\n ")))
def test_spacing_and_capitals_store_as_one_address(typed: str, padding: str) -> None:
    stored = parse_email_address(RawEmailAddressInput(typed))
    shouted = parse_email_address(
        RawEmailAddressInput(padding + typed.upper() + padding)
    )

    assert shouted == stored
