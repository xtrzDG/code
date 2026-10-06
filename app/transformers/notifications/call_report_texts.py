"""
Localized templates of the staff texts about phone calls: the summary
after a call and the note about a caller who did not get through, with
their labels (how a call ended, why a caller did not get through, what
they were sent).
"""

from collections.abc import Mapping

from app.schemas.constants.calls import MissedCallReason, TextBackSkipReason
from app.schemas.constants.conversations import CallOutcome
from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.owner_texts import owner_text

CALL_SUMMARY_TITLE: LocalizedText = owner_text(
    "notifications.call_report.call_summary_title"
)
MISSED_CALL_TITLE: LocalizedText = owner_text(
    "notifications.call_report.missed_call_title"
)
CALLER_LINE: LocalizedText = owner_text("notifications.call_report.caller_line")
HIDDEN_NUMBER: LocalizedText = owner_text("notifications.call_report.hidden_number")
RESULT_LINE: LocalizedText = owner_text("notifications.call_report.result_line")
BOOKING_LINE: LocalizedText = owner_text("notifications.call_report.booking_line")
UNVERIFIED_LINE: LocalizedText = owner_text("notifications.call_report.unverified_line")
REASON_LINE: LocalizedText = owner_text("notifications.call_report.reason_line")
TEXTED_BY_WHATSAPP: LocalizedText = owner_text(
    "notifications.call_report.texted_by_whatsapp"
)
TEXTED_BY_SMS: LocalizedText = owner_text("notifications.call_report.texted_by_sms")
NOT_TEXTED: LocalizedText = owner_text("notifications.call_report.not_texted")
TEXT_BACK_FAILED: LocalizedText = owner_text(
    "notifications.call_report.text_back_failed"
)
MINUTES_AND_SECONDS: LocalizedText = owner_text(
    "notifications.call_report.minutes_and_seconds"
)
SECONDS_ONLY: LocalizedText = owner_text("notifications.call_report.seconds_only")
BRIEF_DETAIL: LocalizedText = owner_text("notifications.call_report.brief_detail")
CALL_OUTCOME_LABELS: Mapping[str, LocalizedText] = {
    CallOutcome.BOOKING: owner_text(
        "notifications.call_report.call_outcome_labels.booking"
    ),
    CallOutcome.LEAD: owner_text("notifications.call_report.call_outcome_labels.lead"),
    CallOutcome.HANDOFF: owner_text(
        "notifications.call_report.call_outcome_labels.handoff"
    ),
    CallOutcome.UNANSWERED_QUESTION: owner_text(
        "notifications.call_report.call_outcome_labels.unanswered_question"
    ),
    CallOutcome.INFORMATION: owner_text(
        "notifications.call_report.call_outcome_labels.information"
    ),
    CallOutcome.ABANDONED: owner_text(
        "notifications.call_report.call_outcome_labels.abandoned"
    ),
}
MISSED_REASON_LABELS: Mapping[str, LocalizedText] = {
    MissedCallReason.NO_ANSWER: owner_text(
        "notifications.call_report.missed_reason_labels.no_answer"
    ),
    MissedCallReason.BUSY: owner_text(
        "notifications.call_report.missed_reason_labels.busy"
    ),
    MissedCallReason.ABANDONED: owner_text(
        "notifications.call_report.missed_reason_labels.abandoned"
    ),
    MissedCallReason.LINE_FAILED: owner_text(
        "notifications.call_report.missed_reason_labels.line_failed"
    ),
    MissedCallReason.NOT_STARTED: owner_text(
        "notifications.call_report.missed_reason_labels.not_started"
    ),
    MissedCallReason.NO_SPEECH: owner_text(
        "notifications.call_report.missed_reason_labels.no_speech"
    ),
    MissedCallReason.TRANSFER_UNANSWERED: owner_text(
        "notifications.call_report.missed_reason_labels.transfer_unanswered"
    ),
}
SKIP_REASON_LABELS: Mapping[str, LocalizedText] = {
    TextBackSkipReason.TURNED_OFF: owner_text(
        "notifications.call_report.skip_reason_labels.turned_off"
    ),
    TextBackSkipReason.OPTED_OUT: owner_text(
        "notifications.call_report.skip_reason_labels.opted_out"
    ),
    TextBackSkipReason.ALREADY_TEXTED: owner_text(
        "notifications.call_report.skip_reason_labels.already_texted"
    ),
    TextBackSkipReason.DAILY_LIMIT: owner_text(
        "notifications.call_report.skip_reason_labels.daily_limit"
    ),
    TextBackSkipReason.IN_CONVERSATION: owner_text(
        "notifications.call_report.skip_reason_labels.in_conversation"
    ),
    TextBackSkipReason.NO_CHANNEL: owner_text(
        "notifications.call_report.skip_reason_labels.no_channel"
    ),
    TextBackSkipReason.NOT_LIVE: owner_text(
        "notifications.call_report.skip_reason_labels.not_live"
    ),
    TextBackSkipReason.NO_CALLER_NUMBER: owner_text(
        "notifications.call_report.skip_reason_labels.no_caller_number"
    ),
    TextBackSkipReason.TOO_LATE: owner_text(
        "notifications.call_report.skip_reason_labels.too_late"
    ),
}
