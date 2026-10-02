from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.handoffs import HandoffUrgency
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.notifications.staff_alerts import (
    StaffAlertBrief,
    StaffAlertBriefInput,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.strings import (
    StaffAlertDetail,
    StaffAlertTitle,
)
from app.transformers.notifications.message_rendering import (
    HANDOFF_REASON_LABELS,
    LEAD_TYPE_LABELS,
    describe_booking_period,
    describe_date,
    render,
    resolve_label,
)
from app.transformers.notifications.staff_alert_texts import (
    BOOKING_DETAIL,
    BOOKING_TITLES,
    HANDOFF_DETAIL,
    HANDOFF_TITLE,
    LEAD_DETAIL_WITH_DATE,
    LEAD_TITLE,
    TEST_DETAIL,
    TEST_TITLE,
    URGENT_HANDOFF_TITLE,
)
from app.utilities.scheduling.localized_formatting import choose_template_language

URGENT_HANDOFF_LEVELS: frozenset[HandoffUrgency] = frozenset(
    {HandoffUrgency.HIGH, HandoffUrgency.CRITICAL}
)


class StaffAlertBriefTransformer(
    TransformerContract[StaffAlertBriefInput, StaffAlertBrief]
):
    """
    The brief of a handoff, request or booking (a test notification when
    no fact is given) in the recipient's language: a title and one line
    for a locked screen, an SMS or an e-mail subject. No customer name,
    phone, message text or summary: those stay behind the link.
    """

    def __init__(self, text_resolver: LocalizedTextResolverContract) -> None:
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def transform(self, input_data: StaffAlertBriefInput) -> StaffAlertBrief:
        business: str = str(input_data.business_name)
        if input_data.handoff is not None:
            title: LocalizedText = (
                URGENT_HANDOFF_TITLE
                if input_data.handoff.urgency in URGENT_HANDOFF_LEVELS
                else HANDOFF_TITLE
            )
            language = self._language(title, input_data)
            reason: str = resolve_label(
                self._text_resolver,
                HANDOFF_REASON_LABELS,
                input_data.handoff.reason,
                language,
            )
            return self._brief(
                title, HANDOFF_DETAIL, language, business, {"reason": reason}
            )

        if input_data.lead is not None:
            language = self._language(LEAD_TITLE, input_data)
            lead_type: str = resolve_label(
                self._text_resolver,
                LEAD_TYPE_LABELS,
                input_data.lead.lead_type,
                language,
            )
            if input_data.lead.requested_date is None:
                return StaffAlertBrief(
                    title=self._title(LEAD_TITLE, language, business),
                    detail=StaffAlertDetail(lead_type),
                )

            date: str = describe_date(input_data.lead.requested_date, language)
            return self._brief(
                LEAD_TITLE,
                LEAD_DETAIL_WITH_DATE,
                language,
                business,
                {"lead_type": lead_type, "date": date},
            )

        if input_data.booking is not None:
            title = BOOKING_TITLES[input_data.booking.change]
            language = self._language(title, input_data)
            booking = input_data.booking.booking
            return self._brief(
                title,
                BOOKING_DETAIL,
                language,
                business,
                {
                    "period": describe_booking_period(booking, language),
                    "party": str(int(booking.party_size)),
                },
            )

        language = self._language(TEST_TITLE, input_data)
        return self._brief(TEST_TITLE, TEST_DETAIL, language, business, {})

    def _language(
        self,
        template: LocalizedText,
        input_data: StaffAlertBriefInput,
    ) -> LanguageTag:
        return choose_template_language(template, input_data.language)

    def _title(
        self,
        template: LocalizedText,
        language: LanguageTag,
        business: str,
    ) -> StaffAlertTitle:
        return StaffAlertTitle(
            render(self._text_resolver, template, language, {"business": business})
        )

    def _brief(
        self,
        title: LocalizedText,
        detail: LocalizedText,
        language: LanguageTag,
        business: str,
        fields: dict[str, str],
    ) -> StaffAlertBrief:
        return StaffAlertBrief(
            title=self._title(title, language, business),
            detail=StaffAlertDetail(
                render(
                    self._text_resolver,
                    detail,
                    language,
                    {"business": business, **fields},
                )
            ),
        )
