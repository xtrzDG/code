"""
Call forwarding codes and the texts every country's guide shows (concept
section 6: "в кабинете — инструкция по переадресации для Magti, Silknet и
Cellfie").

Codes are the GSM supplementary-service codes for conditional forwarding:
**61* no answer, **67* busy, **62* unreachable, ##002# cancels all
forwarding; they work in almost every mobile network. A carrier may want
the number in another format or document another cancel code
(`gsm_code_templates`), or use star codes instead (`StarCodeTemplate`). The
texts live in the owner text catalog (`texts/<language>.json`, keys
`forwarding.*`) in every cabinet language. Step and note placeholders:
{number}, {no_answer_code}, {busy_code}, {unreachable_code}, {cancel_code}.
"""

from collections.abc import Sequence

from app.schemas.constants.localization import (
    CallForwardingCondition,
    ForwardingNumberFormat,
    TextReviewStatus,
)
from app.schemas.dto.catalog.call_forwarding import (
    CallForwardingCodeTemplate,
    CarrierForwardingGuide,
    StarCodeTemplate,
)
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import (
    CallForwardingDialCodeTemplate,
)
from app.schemas.typings.localization.strings import CarrierName
from app.utilities.localization.owner_texts import (
    has_owner_text,
    owner_text,
    owner_text_list,
)

GSM_CONDITION_CODE_TEMPLATES: dict[CallForwardingCondition, str] = {
    CallForwardingCondition.NO_ANSWER: "**61*{number}#",
    CallForwardingCondition.BUSY: "**67*{number}#",
    CallForwardingCondition.UNREACHABLE: "**62*{number}#",
}
STANDARD_CANCEL_CODE: CallForwardingDialCodeTemplate = CallForwardingDialCodeTemplate(
    "##002#"
)


def gsm_code_templates(
    number_format: ForwardingNumberFormat,
    cancel_code: CallForwardingDialCodeTemplate = STANDARD_CANCEL_CODE,
) -> tuple[CallForwardingCodeTemplate, ...]:
    """
    The GSM codes (no answer, busy, unreachable, cancel) with the number in
    the carrier's format, and the carrier's cancel code where it documents
    another one than ##002#.
    """

    dial_code_templates: dict[
        CallForwardingCondition, CallForwardingDialCodeTemplate
    ] = {
        condition: CallForwardingDialCodeTemplate(dial_code_template)
        for condition, dial_code_template in GSM_CONDITION_CODE_TEMPLATES.items()
    }
    dial_code_templates[CallForwardingCondition.CANCEL_ALL] = cancel_code
    return tuple(
        CallForwardingCodeTemplate(
            condition=condition,
            dial_code_template=dial_code_template,
            descriptions=owner_text(f"forwarding.codes.{condition.value}"),
            number_format=number_format,
        )
        for condition, dial_code_template in dial_code_templates.items()
    )


GSM_CODE_TEMPLATES: tuple[CallForwardingCodeTemplate, ...] = gsm_code_templates(
    ForwardingNumberFormat.E164
)
FORWARDING_STEPS: tuple[LocalizedText, ...] = owner_text_list("forwarding.steps")
FORWARDING_NOTES: tuple[LocalizedText, ...] = owner_text_list("forwarding.notes")
# Follows the note of a carrier whose codes are its own, not the standard GSM
# set, while they are not confirmed yet; that note names the carrier.
UNCONFIRMED_CARRIER_CODES_NOTE: LocalizedText = owner_text(
    "forwarding.carrier_unconfirmed_codes"
)


def carrier(
    country: str,
    slug: str,
    name: str,
    review_status: TextReviewStatus = TextReviewStatus.NEEDS_REVIEW,
    code_templates: Sequence[CallForwardingCodeTemplate] = GSM_CODE_TEMPLATES,
    star_code_templates: Sequence[StarCodeTemplate] = (),
) -> CarrierForwardingGuide:
    """
    A carrier with its codes (the GSM ones unless it has its own) and its
    catalog note, when it has one.
    """

    note_key: str = f"forwarding.carriers.{country}.{slug}.note"
    return CarrierForwardingGuide(
        carrier_name=CarrierName(name),
        code_templates=list(code_templates),
        notes=owner_text(note_key) if has_owner_text(note_key) else None,
        review_status=review_status,
        star_code_templates=list(star_code_templates),
    )
