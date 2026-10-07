"""
Call forwarding codes and the texts every country's guide shows (concept
section 6: "в кабинете — инструкция по переадресации для Magti, Silknet и
Cellfie").

Codes are the GSM supplementary-service codes for conditional forwarding:
**61* no answer, **67* busy, **62* unreachable, ##002# cancels all
forwarding; they work in almost every mobile network. The texts live in the
owner text catalog (`texts/<language>.json`, keys `forwarding.*`) in every
cabinet language. Step and note placeholders: {number}, {no_answer_code},
{busy_code}, {unreachable_code}, {cancel_code}.
"""

from app.schemas.constants.localization import CallForwardingCondition
from app.schemas.dto.catalog.call_forwarding import CallForwardingCodeTemplate
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import (
    CallForwardingDialCodeTemplate,
)
from app.utilities.localization.owner_texts import owner_text, owner_text_list

GSM_DIAL_CODE_TEMPLATES: dict[CallForwardingCondition, str] = {
    CallForwardingCondition.NO_ANSWER: "**61*{number}#",
    CallForwardingCondition.BUSY: "**67*{number}#",
    CallForwardingCondition.UNREACHABLE: "**62*{number}#",
    CallForwardingCondition.CANCEL_ALL: "##002#",
}
GSM_CODE_TEMPLATES: tuple[CallForwardingCodeTemplate, ...] = tuple(
    CallForwardingCodeTemplate(
        condition=condition,
        dial_code_template=CallForwardingDialCodeTemplate(dial_code_template),
        descriptions=owner_text(f"forwarding.codes.{condition.value}"),
    )
    for condition, dial_code_template in GSM_DIAL_CODE_TEMPLATES.items()
)


FORWARDING_STEPS: tuple[LocalizedText, ...] = owner_text_list("forwarding.steps")
FORWARDING_NOTES: tuple[LocalizedText, ...] = owner_text_list("forwarding.notes")
