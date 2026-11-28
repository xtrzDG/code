"""
Call forwarding: carrier guides and the instructions for a business's
phone number.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.localization import (
    CallForwardingCondition,
    ForwardingNumberFormat,
    StarCodeCondition,
    TextReviewStatus,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.booleans import IsCarrierChoiceNeeded
from app.schemas.typings.localization.constrained_strings import (
    CallForwardingDialCode,
    CallForwardingDialCodeTemplate,
    CountryCode,
    E164PhoneNumber,
    LanguageTag,
    VerticalServiceDialCode,
    VerticalServiceDialCodeTemplate,
)
from app.schemas.typings.localization.strings import (
    CarrierName,
    FormattedPhoneNumber,
    InstructionText,
)
from app.schemas.typings.users.prefixed_id import UserId


class CallForwardingCodeTemplate(ImmutableDTO):
    """
    A GSM forwarding code before the assistant's number is filled in, in
    the number format the carrier asks for.
    """

    condition: CallForwardingCondition
    dial_code_template: CallForwardingDialCodeTemplate
    descriptions: LocalizedText
    number_format: ForwardingNumberFormat = ForwardingNumberFormat.E164


class StarCodeTemplate(ImmutableDTO):
    """
    A North American star code (Verizon's *71) before the assistant's
    number is filled in; star codes take the national digits.
    """

    condition: StarCodeCondition
    dial_code_template: VerticalServiceDialCodeTemplate
    descriptions: LocalizedText
    number_format: ForwardingNumberFormat = ForwardingNumberFormat.NATIONAL_DIGITS


class CarrierForwardingGuide(ImmutableDTO):
    """
    Forwarding codes of one named mobile carrier: GSM codes, star codes or
    both.

    NEEDS_REVIEW: the codes are not yet checked against the carrier's own
    documentation (the standard GSM ones, or codes known only from summaries
    of the carrier's pages); owners read that they are unconfirmed (after
    `notes`, which hold what is known of the carrier).
    """

    carrier_name: CarrierName
    code_templates: list[CallForwardingCodeTemplate]
    notes: LocalizedText | None = None
    review_status: TextReviewStatus = TextReviewStatus.REVIEWED
    star_code_templates: list[StarCodeTemplate] = Field(
        default_factory=list[StarCodeTemplate]
    )


class CountryForwardingTexts(ImmutableDTO):
    """
    A country's own top-level codes, steps and notes in place of the
    standard GSM ones. `is_carrier_choice_needed`: its carriers take
    different codes, so the steps send the owner to their carrier first.
    """

    code_templates: list[CallForwardingCodeTemplate]
    steps: list[LocalizedText]
    notes: list[LocalizedText]
    is_carrier_choice_needed: IsCarrierChoiceNeeded = False


class CallForwardingGuide(ImmutableDTO):
    """
    How owners in one country forward unanswered calls to the assistant.

    Step and note texts are templates with the placeholders {number},
    {no_answer_code}, {busy_code}, {unreachable_code} and {cancel_code}.
    With `is_carrier_choice_needed` the owner opens their carrier first and
    the top-level codes are the standard ones for carriers not listed.
    """

    country_code: CountryCode
    code_templates: list[CallForwardingCodeTemplate]
    carriers: list[CarrierForwardingGuide] = Field(
        default_factory=list[CarrierForwardingGuide]
    )
    steps: list[LocalizedText]
    notes: list[LocalizedText] = Field(default_factory=list[LocalizedText])
    is_carrier_choice_needed: IsCarrierChoiceNeeded = False


class CallForwardingInstructionsRequest(ImmutableDTO):
    """
    Cabinet request for forwarding instructions.

    Without a display language the owner language of the business is used.
    """

    user_id: UserId
    business_id: BusinessId
    display_language: LanguageTag | None = None


class CallForwardingInstructionsQuery(ImmutableDTO):
    """Forwarding instructions for a business the caller may act on."""

    business: BusinessDocument
    display_language: LanguageTag


class CallForwardingCode(ImmutableDTO):
    """A ready-to-dial forwarding code."""

    condition: CallForwardingCondition
    dial_code: CallForwardingDialCode
    description: InstructionText


class CallForwardingStarCode(ImmutableDTO):
    """A ready-to-dial North American star code (Verizon's *71 and *73)."""

    condition: StarCodeCondition
    dial_code: VerticalServiceDialCode
    description: InstructionText


class CarrierForwardingInstructions(ImmutableDTO):
    """
    Ready-to-dial codes of one named mobile carrier: GSM codes (`codes`)
    and star codes (`star_codes`), either of them possibly empty.
    """

    carrier_name: CarrierName
    codes: list[CallForwardingCode]
    note: InstructionText | None = None
    star_codes: list[CallForwardingStarCode] = Field(
        default_factory=list[CallForwardingStarCode]
    )


class CallForwardingInstructions(ImmutableDTO):
    """
    Step-by-step forwarding of "no answer / busy / unreachable" calls from the
    venue's phone to the assistant's number (concept section 6).

    Texts are in the display language when available, else in English.
    `is_carrier_choice_needed`: the country's carriers take different codes
    (the United States), so the owner opens their own carrier first and the
    top-level `codes` are the standard codes for carriers not listed.
    """

    business_id: BusinessId
    country_code: CountryCode
    display_language: LanguageTag
    assistant_phone_number: E164PhoneNumber
    assistant_phone_number_display: FormattedPhoneNumber
    codes: list[CallForwardingCode]
    carriers: list[CarrierForwardingInstructions] = Field(
        default_factory=list[CarrierForwardingInstructions]
    )
    steps: list[InstructionText]
    notes: list[InstructionText] = Field(default_factory=list[InstructionText])
    is_carrier_choice_needed: IsCarrierChoiceNeeded = False
