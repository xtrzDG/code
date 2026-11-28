"""
Forwarding codes ready to dial: the assistant's number written the way each
code asks for it and filled into the code's template.

A carrier's number format describes numbers of its own country. An
assistant number of another country goes into GSM codes in E.164, the
international form GSM networks take, and gets no star codes: they carry
North American national digits only, and those carriers forward to no
other country.
"""

from collections.abc import Callable, Sequence

from app.schemas.constants.localization import ForwardingNumberFormat
from app.schemas.dto.catalog.call_forwarding import (
    CallForwardingCode,
    CallForwardingCodeTemplate,
    CallForwardingStarCode,
    CarrierForwardingGuide,
    CarrierForwardingInstructions,
    StarCodeTemplate,
)
from app.schemas.dto.localization import LocalizedText, PhoneNumberDetails
from app.schemas.typings.localization.constrained_strings import (
    CallForwardingDialCode,
    CountryCode,
    ForwardingTargetNumber,
    VerticalServiceDialCode,
)
from app.schemas.typings.localization.strings import InstructionText

NUMBER_PLACEHOLDER: str = "{number}"

# A catalog text in the display language (a code's description).
type DescribeText = Callable[[LocalizedText], InstructionText]


def render_carrier(
    carrier: CarrierForwardingGuide,
    number: PhoneNumberDetails,
    carrier_country: CountryCode,
    describe: DescribeText,
    note: InstructionText | None,
) -> CarrierForwardingInstructions:
    """A carrier's ready-to-dial GSM and star codes, with its rendered note."""

    codes: list[CallForwardingCode] = render_gsm_codes(
        carrier.code_templates, number, carrier_country, describe
    )
    star_codes: list[CallForwardingStarCode] = render_star_codes(
        carrier.star_code_templates, number, carrier_country, describe
    )
    return CarrierForwardingInstructions(
        carrier_name=carrier.carrier_name,
        codes=codes,
        note=note,
        star_codes=star_codes,
    )


def forwarding_target(
    number: PhoneNumberDetails,
    number_format: ForwardingNumberFormat,
) -> ForwardingTargetNumber:
    """
    The number as a code carries it: in E.164 ("+12125550123"), as the
    national digits ("2125550123") or as the digits with the country code
    ("12125550123").
    """

    e164: str = str(number.e164)
    if number_format is ForwardingNumberFormat.E164:
        return ForwardingTargetNumber(e164)

    digits: str = e164.removeprefix("+")
    if number_format is ForwardingNumberFormat.DIGITS_WITH_COUNTRY_CODE:
        return ForwardingTargetNumber(digits)

    return ForwardingTargetNumber(digits.removeprefix(str(int(number.calling_code))))


def render_gsm_codes(
    templates: Sequence[CallForwardingCodeTemplate],
    number: PhoneNumberDetails,
    carrier_country: CountryCode,
    describe: DescribeText,
) -> list[CallForwardingCode]:
    """The GSM codes with the number filled in (E.164 when it is foreign)."""

    return [
        CallForwardingCode(
            condition=template.condition,
            dial_code=CallForwardingDialCode(
                filled(
                    str(template.dial_code_template),
                    number,
                    carried_format(number, template.number_format, carrier_country),
                )
            ),
            description=describe(template.descriptions),
        )
        for template in templates
    ]


def render_star_codes(
    templates: Sequence[StarCodeTemplate],
    number: PhoneNumberDetails,
    carrier_country: CountryCode,
    describe: DescribeText,
) -> list[CallForwardingStarCode]:
    """The star codes with the number filled in; none for a foreign number."""

    if number.country_code != carrier_country:
        return []

    return [
        CallForwardingStarCode(
            condition=template.condition,
            dial_code=VerticalServiceDialCode(
                filled(str(template.dial_code_template), number, template.number_format)
            ),
            description=describe(template.descriptions),
        )
        for template in templates
    ]


def carried_format(
    number: PhoneNumberDetails,
    number_format: ForwardingNumberFormat,
    carrier_country: CountryCode,
) -> ForwardingNumberFormat:
    """The carrier's format for a number of its country, E.164 for another."""

    if number.country_code == carrier_country:
        return number_format

    return ForwardingNumberFormat.E164


def filled(
    template: str,
    number: PhoneNumberDetails,
    number_format: ForwardingNumberFormat,
) -> str:
    """
    A code template with the number in its place; a template without
    "{number}" stays as it is.
    """

    return template.replace(
        NUMBER_PLACEHOLDER, str(forwarding_target(number, number_format))
    )
