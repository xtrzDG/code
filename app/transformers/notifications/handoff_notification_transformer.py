from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.operations import HandoffStaffNotificationInput
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.notifications.message_rendering import (
    CHANNEL_LABELS,
    HANDOFF_REASON_LABELS,
    HANDOFF_URGENCY_LABELS,
    describe_phone,
    localized,
    render,
    resolve_label,
    text_or_missing,
)
from app.utilities.scheduling.localized_formatting import choose_template_language

HANDOFF: LocalizedText = localized(
    en="[{urgency}] A customer needs a person · {business}\nReason: {reason}\n"
    "{summary}\nName: {name}\nPhone: {phone}\nChannel: {channel}",
    ru="[{urgency}] Клиенту нужен человек · {business}\nПричина: {reason}\n"
    "{summary}\nИмя: {name}\nТелефон: {phone}\nКанал: {channel}",
    ka="[{urgency}] კლიენტს ადამიანი სჭირდება · {business}\nმიზეზი: {reason}\n"
    "{summary}\nსახელი: {name}\nტელეფონი: {phone}\nარხი: {channel}",
)


class HandoffNotificationTransformer(
    TransformerContract[HandoffStaffNotificationInput, MessageText]
):
    """
    Staff notification about a handoff (concept: short retelling and the
    customer's contact) with urgency, reason, name, phone in international
    format and channel, in the staff member's language.
    """

    def __init__(self, text_resolver: LocalizedTextResolverContract) -> None:
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def transform(self, input_data: HandoffStaffNotificationInput) -> MessageText:
        language: LanguageTag = choose_template_language(HANDOFF, input_data.language)
        return MessageText(
            render(
                self._text_resolver,
                HANDOFF,
                language,
                {
                    "urgency": resolve_label(
                        self._text_resolver,
                        HANDOFF_URGENCY_LABELS,
                        input_data.urgency,
                        language,
                    ),
                    "business": str(input_data.business_name),
                    "reason": resolve_label(
                        self._text_resolver,
                        HANDOFF_REASON_LABELS,
                        input_data.reason,
                        language,
                    ),
                    "summary": str(input_data.summary),
                    "name": text_or_missing(input_data.contact_name),
                    "phone": describe_phone(input_data.contact_phone_display, None),
                    "channel": resolve_label(
                        self._text_resolver,
                        CHANNEL_LABELS,
                        input_data.channel,
                        language,
                    ),
                },
            )
        )
