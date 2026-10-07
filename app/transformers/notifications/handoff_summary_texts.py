"""
Localized texts of the handoffs the platform creates itself (a reply that
failed, figures the guard held back, a reply that never arrived, erased
data): what happened, then the quoted words. The cabinet keeps the same
texts in its `handoffs.summaryCodes` dictionary.
"""

from collections.abc import Mapping

from app.schemas.constants.handoffs import HandoffSummaryCode
from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.owner_texts import owner_text

# What happened, for a code that lists no flagged values.
SUMMARY_TEXTS: Mapping[HandoffSummaryCode, LocalizedText] = {
    HandoffSummaryCode.MODEL_DECLINED: owner_text(
        "notifications.handoff_summary.summary_texts.model_declined"
    ),
    HandoffSummaryCode.MODEL_UNAVAILABLE: owner_text(
        "notifications.handoff_summary.summary_texts.model_unavailable"
    ),
    HandoffSummaryCode.ANSWER_UNFINISHED: owner_text(
        "notifications.handoff_summary.summary_texts.answer_unfinished"
    ),
    HandoffSummaryCode.UNVERIFIED_VALUES: owner_text(
        "notifications.handoff_summary.summary_texts.unverified_values"
    ),
    HandoffSummaryCode.CALL_BOOKING_UNVERIFIED_VALUES: owner_text(
        "notifications.handoff_summary.summary_texts.call_booking_unverified_values"
    ),
    HandoffSummaryCode.CALL_REQUEST_UNVERIFIED_VALUES: owner_text(
        "notifications.handoff_summary.summary_texts.call_request_unverified_values"
    ),
    HandoffSummaryCode.REPLY_UNDELIVERED: owner_text(
        "notifications.handoff_summary.summary_texts.reply_undelivered"
    ),
    HandoffSummaryCode.DATA_ERASED: owner_text(
        "notifications.handoff_summary.summary_texts.data_erased"
    ),
}
# What happened, for a code with flagged values: `{values}` lists them.
SUMMARY_TEXTS_WITH_VALUES: Mapping[HandoffSummaryCode, LocalizedText] = {
    HandoffSummaryCode.UNVERIFIED_VALUES: owner_text(
        "notifications.handoff_summary.summary_texts_with_values.unverified_values"
    ),
    HandoffSummaryCode.CALL_BOOKING_UNVERIFIED_VALUES: owner_text(
        "notifications.handoff_summary.summary_texts_with_values.call_booking_unverified_values"
    ),
    HandoffSummaryCode.CALL_REQUEST_UNVERIFIED_VALUES: owner_text(
        "notifications.handoff_summary.summary_texts_with_values.call_request_unverified_values"
    ),
}
# The quoted words: the reply that did not arrive, else the customer's.
QUOTED_REPLY: LocalizedText = owner_text("notifications.handoff_summary.quoted_reply")
QUOTED_CUSTOMER_MESSAGE: LocalizedText = owner_text(
    "notifications.handoff_summary.quoted_customer_message"
)
VALUE_SEPARATOR: str = ", "
