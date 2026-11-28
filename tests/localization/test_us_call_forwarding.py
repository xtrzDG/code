"""
United States: forwarding by carrier. Verizon's star codes, T-Mobile's and
AT&T's GSM codes in their own number formats, the standard codes with the
number as 1 and 10 digits for every other carrier, and every carrier a
draft until a person checks its pages. The rules every country's guide
follows are in test_forwarding_code_policies.
"""

import pytest

from app.registries.localization.call_forwarding_guide_registry import (
    CallForwardingGuideRegistry,
)
from app.schemas.constants.localization import (
    CABINET_LANGUAGES,
    CallForwardingCondition,
    ForwardingNumberFormat,
    StarCodeCondition,
    TextReviewStatus,
)
from app.schemas.dto.catalog.call_forwarding import (
    CallForwardingCode,
    CallForwardingInstructions,
    CarrierForwardingInstructions,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    ForwardingTargetNumber,
    LanguageTag,
    VerticalServiceDialCode,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.localization.forwarding_code_rendering import forwarding_target
from app.utilities.localization.phone_number_parser import PhoneNumberParser
from tests.localization.builders import build_business
from tests.localization.cabinet_builders import add_phone_channel, build_cabinet_world
from tests.localization.test_call_forwarding import request_instructions

US_ASSISTANT_NUMBER: str = "+12125550123"
UNCONFIRMED_CODES: str = (
    "Codes not yet confirmed with the carrier: if a code fails, ask the "
    "carrier's support."
)
NO_ANSWER = CallForwardingCondition.NO_ANSWER
BUSY = CallForwardingCondition.BUSY
UNREACHABLE = CallForwardingCondition.UNREACHABLE
CANCEL_ALL = CallForwardingCondition.CANCEL_ALL


def us_instructions(
    language: str | None = None, number: str = US_ASSISTANT_NUMBER
) -> CallForwardingInstructions:
    world = build_cabinet_world()
    owner_id = UserId()
    business = build_business(owner_id, "US", "en")
    world.business_repo.save(business)
    add_phone_channel(world, business, number)
    return request_instructions(world, business, owner_id, language)


def carriers_by_name(
    instructions: CallForwardingInstructions,
) -> dict[str, CarrierForwardingInstructions]:
    return {str(carrier.carrier_name): carrier for carrier in instructions.carriers}


def dial_codes(codes: list[CallForwardingCode]) -> dict[CallForwardingCondition, str]:
    return {code.condition: str(code.dial_code) for code in codes}


def test_each_us_carrier_gets_the_codes_it_documents() -> None:
    carriers = carriers_by_name(us_instructions())

    assert list(carriers) == ["Verizon", "T-Mobile", "AT&T"]
    verizon = carriers["Verizon"]
    assert verizon.codes == []
    assert [(code.condition, str(code.dial_code)) for code in verizon.star_codes] == [
        (StarCodeCondition.NO_ANSWER_OR_BUSY, "*712125550123"),
        (StarCodeCondition.CANCEL_ALL, "*73"),
    ]
    assert all(
        type(code.dial_code) is VerticalServiceDialCode for code in verizon.star_codes
    )
    assert dial_codes(carriers["T-Mobile"].codes) == {
        NO_ANSWER: "**61*12125550123#",
        BUSY: "**67*12125550123#",
        UNREACHABLE: "**62*12125550123#",
        CANCEL_ALL: "##004#",
    }
    assert dial_codes(carriers["AT&T"].codes) == {
        NO_ANSWER: "**61*2125550123#",
        BUSY: "**67*2125550123#",
        UNREACHABLE: "**62*2125550123#",
        CANCEL_ALL: "##002#",
    }
    assert carriers["T-Mobile"].star_codes == carriers["AT&T"].star_codes == []


def test_other_us_carriers_read_the_standard_codes_after_the_carrier_choice() -> None:
    instructions = us_instructions()

    assert instructions.is_carrier_choice_needed is True
    assert dial_codes(instructions.codes) == {
        NO_ANSWER: "**61*12125550123#",
        BUSY: "**67*12125550123#",
        UNREACHABLE: "**62*12125550123#",
        CANCEL_ALL: "##002#",
    }
    assert instructions.steps[1] == (
        "Open your carrier below and dial its codes one at a time: calls you do "
        "not answer go to the assistant at +1 212-555-0123."
    )
    assert instructions.steps[2] == (
        "Carrier not listed? Try the standard codes under Other carriers."
    )


def test_every_us_carrier_is_a_draft_and_says_so() -> None:
    guide = CallForwardingGuideRegistry().get(CountryCode("US"))
    english, italian = LanguageTag("en"), LanguageTag("it")

    assert {carrier.review_status for carrier in guide.carriers} == {
        TextReviewStatus.NEEDS_REVIEW
    }
    notes = {
        str(carrier.carrier_name): carrier.notes
        for carrier in guide.carriers
        if carrier.notes is not None
    }
    assert notes["Verizon"].values[english].endswith(f". {UNCONFIRMED_CODES}")
    assert notes["T-Mobile"].values[english].endswith(f". {UNCONFIRMED_CODES}")
    assert (
        notes["AT&T"]
        .values[english]
        .endswith(
            ". Standard GSM codes, not yet confirmed with AT&T: if a code fails, ask "
            "AT&T support."
        )
    )
    for note in notes.values():
        assert "non ancora confermati con" in note.values[italian]


@pytest.mark.parametrize(
    ("language", "expected_step"),
    [
        ("en", "Open your carrier below"),
        ("it", "Apri il tuo operatore qui sotto"),
    ],
)
def test_every_us_text_renders_without_braces(
    language: str, expected_step: str
) -> None:
    instructions = us_instructions(language)
    carriers = instructions.carriers

    texts = [*instructions.steps, *instructions.notes]
    texts.extend(carrier.note for carrier in carriers if carrier.note is not None)
    texts.extend(code.description for code in instructions.codes)
    for carrier in carriers:
        texts.extend(code.description for code in carrier.codes)
        texts.extend(code.description for code in carrier.star_codes)

    assert instructions.steps[1].startswith(expected_step)
    assert "+1 212-555-0123" in instructions.steps[1]
    # 5 steps, 5 notes, 3 carrier notes, 4 + 2 + 4 + 4 code descriptions.
    assert len(texts) == 27
    assert [text for text in texts if "{" in text or "}" in text] == []


def test_every_us_text_exists_in_every_cabinet_language() -> None:
    guide = CallForwardingGuideRegistry().get(CountryCode("US"))
    texts = [*guide.steps, *guide.notes]
    texts.extend(
        carrier.notes for carrier in guide.carriers if carrier.notes is not None
    )
    for carrier in guide.carriers:
        texts.extend(template.descriptions for template in carrier.star_code_templates)

    for text in texts:
        assert {str(tag) for tag in text.values} == {
            language.value for language in CABINET_LANGUAGES
        }


@pytest.mark.parametrize("number", ["+390212345678", "+14165550123"])
def test_an_assistant_number_abroad_is_dialled_in_e164_without_star_codes(
    number: str,
) -> None:
    instructions = us_instructions(number=number)
    carriers = carriers_by_name(instructions)

    # US carriers forward to US numbers only; the codes stay well-formed.
    assert carriers["Verizon"].star_codes == []
    for codes in (
        instructions.codes,
        carriers["T-Mobile"].codes,
        carriers["AT&T"].codes,
    ):
        assert dial_codes(codes)[NO_ANSWER] == f"**61*{number}#"


@pytest.mark.parametrize(
    ("number", "number_format", "expected"),
    [
        (US_ASSISTANT_NUMBER, ForwardingNumberFormat.E164, "+12125550123"),
        (US_ASSISTANT_NUMBER, ForwardingNumberFormat.NATIONAL_DIGITS, "2125550123"),
        (
            US_ASSISTANT_NUMBER,
            ForwardingNumberFormat.DIGITS_WITH_COUNTRY_CODE,
            "12125550123",
        ),
        ("+390212345678", ForwardingNumberFormat.NATIONAL_DIGITS, "0212345678"),
    ],
)
def test_the_number_is_written_as_the_carrier_asks(
    number: str, number_format: ForwardingNumberFormat, expected: str
) -> None:
    details = PhoneNumberParser().parse(RawPhoneNumberInput(number), None)

    target = forwarding_target(details, number_format)

    assert target == expected
    assert type(target) is ForwardingTargetNumber
