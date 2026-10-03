"""
The staff alert about a call (its summary, or the note about a caller who
did not get through) and its texts in every recipient's language.
"""

from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.conversations import CallOutcome
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.notifications import StaffAlertEvent, StaffLinkTarget
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import CallSummary
from app.schemas.dto.calls.call_summaries import CallReportTextInput
from app.schemas.dto.notifications.staff_alerts import StaffAlert, StaffAlertBrief
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import (
    PushNotificationTag,
    StaffAlertSubject,
)
from app.use_cases.shared.staff_alerts import StaffAlertTexts
from app.use_cases.voice.summaries.call_summary_writer import pick_summary

# A summary after every call goes to the chats staff linked (it carries the
# summary) and to devices; e-mail and SMS would only say "a call ended".
SUMMARY_CHANNELS: list[ManagerContactChannel] = [
    ManagerContactChannel.TELEGRAM,
    ManagerContactChannel.WHATSAPP,
]
# Who wants to hear about a call: those following bookings hear about one
# that booked, those following handoffs about one passed to a person, and
# every other call (a missed caller included) is a request.
OUTCOME_EVENTS: dict[CallOutcome, StaffAlertEvent] = {
    CallOutcome.BOOKING: StaffAlertEvent.BOOKING,
    CallOutcome.HANDOFF: StaffAlertEvent.HANDOFF,
}


def call_report_alert(
    business: BusinessDocument,
    subject: StaffAlertSubject,
    conversation_id: ConversationId | None,
    outcome: CallOutcome | None,
    is_missed: bool,
) -> StaffAlert:
    """
    Once per call and recipient (`subject`); it opens the call's
    conversation. A missed caller is told about on every channel (staff
    should call back), a summary only in linked chats and on devices.
    """

    return StaffAlert(
        business_id=business.id,
        event=(
            StaffAlertEvent.LEAD
            if outcome is None or is_missed
            else OUTCOME_EVENTS.get(outcome, StaffAlertEvent.LEAD)
        ),
        target=StaffLinkTarget.CONVERSATION,
        conversation_id=conversation_id,
        tag=PushNotificationTag(str(subject)),
        subject=subject,
        contact_channels=None if is_missed else list(SUMMARY_CHANNELS),
    )


def call_report_texts(
    facts: CallReportTextInput,
    summaries: list[CallSummary],
    detailed: TransformerContract[CallReportTextInput, MessageText],
    brief: TransformerContract[CallReportTextInput, StaffAlertBrief],
) -> StaffAlertTexts:
    """The texts of the facts in a recipient's language, with its summary."""

    def in_language(language: LanguageTag) -> CallReportTextInput:
        summary: CallSummary | None = pick_summary(summaries, language)
        return facts.model_copy(
            update={
                "language": language,
                "summary": None if summary is None else summary.text,
            }
        )

    def render(language: LanguageTag) -> MessageText:
        return detailed.transform(in_language(language))

    def render_brief(language: LanguageTag) -> StaffAlertBrief:
        return brief.transform(in_language(language))

    return StaffAlertTexts(detailed=render, brief=render_brief)


def staff_languages(business: BusinessDocument) -> list[LanguageTag]:
    """The languages of the staff contacts that get detailed texts."""

    return [
        contact.language
        for contact in business.manager_contacts
        if contact.channel in SUMMARY_CHANNELS
    ]
