from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.operations import LeadStaffNotificationInput
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.notifications.message_rendering import (
    CHANNEL_LABELS,
    LEAD_TYPE_LABELS,
    describe_date,
    describe_phone,
    localized,
    render,
    resolve_label,
    text_or_missing,
)
from app.utilities.scheduling.localized_formatting import choose_template_language

NEW_LEAD: LocalizedText = localized(
    en="New request · {business}\nType: {lead_type}\n{details}\nName: {name}\n"
    "Phone: {phone}\nChannel: {channel}",
    ru="Новая заявка · {business}\nТип: {lead_type}\n{details}\nИмя: {name}\n"
    "Телефон: {phone}\nКанал: {channel}",
    ka="ახალი მოთხოვნა · {business}\nტიპი: {lead_type}\n{details}\n"
    "სახელი: {name}\nტელეფონი: {phone}\nარხი: {channel}",
)
REQUESTED_DATE_LINE: LocalizedText = localized(
    en="Date: {date}",
    ru="Дата: {date}",
    ka="თარიღი: {date}",
)
PARTY_SIZE_LINE: LocalizedText = localized(
    en="Guests: {party}",
    ru="Гостей: {party}",
    ka="სტუმრები: {party}",
)
BUDGET_LINE: LocalizedText = localized(
    en="Budget: {budget}",
    ru="Бюджет: {budget}",
    ka="ბიუჯეტი: {budget}",
)


class NewLeadNotificationTransformer(
    TransformerContract[LeadStaffNotificationInput, MessageText]
):
    """
    Staff notification about a new request (banquet, group, order...), with
    the requested date, party size and budget when the customer gave them.
    """

    def __init__(self, text_resolver: LocalizedTextResolverContract) -> None:
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def transform(self, input_data: LeadStaffNotificationInput) -> MessageText:
        language: LanguageTag = choose_template_language(NEW_LEAD, input_data.language)
        lead = input_data.lead
        lines: list[str] = [
            render(
                self._text_resolver,
                NEW_LEAD,
                language,
                {
                    "business": str(input_data.business_name),
                    "lead_type": resolve_label(
                        self._text_resolver, LEAD_TYPE_LABELS, lead.lead_type, language
                    ),
                    "details": str(lead.details),
                    "name": text_or_missing(input_data.contact_name),
                    "phone": describe_phone(input_data.contact_phone_display, None),
                    "channel": resolve_label(
                        self._text_resolver,
                        CHANNEL_LABELS,
                        lead.source_channel,
                        language,
                    ),
                },
            )
        ]
        if lead.requested_date is not None:
            lines.append(
                render(
                    self._text_resolver,
                    REQUESTED_DATE_LINE,
                    language,
                    {"date": describe_date(lead.requested_date, language)},
                )
            )

        if lead.party_size is not None:
            lines.append(
                render(
                    self._text_resolver,
                    PARTY_SIZE_LINE,
                    language,
                    {"party": str(int(lead.party_size))},
                )
            )

        if lead.budget is not None:
            lines.append(
                render(
                    self._text_resolver,
                    BUDGET_LINE,
                    language,
                    {"budget": str(lead.budget)},
                )
            )

        return MessageText("\n".join(lines))
