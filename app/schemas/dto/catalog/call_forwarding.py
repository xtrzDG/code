"""
Call forwarding: carrier guides and the instructions for a business's
phone number.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.localization import (
    CallForwardingCondition,
    TextReviewStatus,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import (
    CallForwardingDialCode,
    CallForwardingDialCodeTemplate,
    CountryCode,
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.localization.strings import (
    CarrierName,
    FormattedPhoneNumber,
    InstructionText,
)
from app.schemas.typings.users.prefixed_id import UserId


class CallForwardingCodeTemplate(ImmutableDTO):
    """A forwarding code before the assistant's number is filled in."""

    condition: CallForwardingCondition
    dial_code_template: CallForwardingDialCodeTemplate
    descriptions: LocalizedText


class CarrierForwardingGuide(ImmutableDTO):
    """
    Forwarding codes of one named mobile carrier.

    NEEDS_REVIEW: the codes are the standard GSM ones, not yet checked
    against the carrier's own documentation; owners read that they are
    unconfirmed (after `notes`, which hold what is known of the carrier).
    """

    carrier_name: CarrierName
    code_templates: list[CallForwardingCodeTemplate]
    notes: LocalizedText | None = None
    review_status: TextReviewStatus = TextReviewStatus.REVIEWED


class CallForwardingGuide(ImmutableDTO):
    """
    How owners in one country forward unanswered calls to the assistant.

    Step and note texts are templates with the placeholders {number},
    {no_answer_code}, {busy_code}, {unreachable_code} and {cancel_code}.
    """

    country_code: CountryCode
    code_templates: list[CallForwardingCodeTemplate]
    carriers: list[CarrierForwardingGuide] = Field(
        default_factory=list[CarrierForwardingGuide]
    )
    steps: list[LocalizedText]
    notes: list[LocalizedText] = Field(default_factory=list[LocalizedText])


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


class CarrierForwardingInstructions(ImmutableDTO):
    """Ready-to-dial codes of one named mobile carrier."""

    carrier_name: CarrierName
    codes: list[CallForwardingCode]
    note: InstructionText | None = None


class CallForwardingInstructions(ImmutableDTO):
    """
    Step-by-step forwarding of "no answer / busy / unreachable" calls from the
    venue's phone to the assistant's number (concept section 6).

    Texts are in the display language when available, else in English.
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
