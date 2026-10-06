"""
The handoff of a website chat whose answer never came: the widget waited
past its limit (no worker answered in time), told the visitor that a
person will answer, and passes the conversation on. Staff read it like
the platform's other failed answers: "The assistant was briefly
unavailable and could not answer", with the visitor's last message.
"""

from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.handoffs import (
    HandoffReason,
    HandoffSummaryCode,
    HandoffUrgency,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.channels.widget_handoff import WidgetHandoffTarget
from app.schemas.dto.handoffs import CodedHandoffSummary
from app.schemas.typings.handoffs.strings import HandoffQuotedText
from app.schemas.typings.localization.constrained_strings import LanguageTag

# Longer messages are cut: the conversation itself has the whole text.
MAX_QUOTED_MESSAGE_LENGTH: int = 300


def no_answer_target(
    business: BusinessDocument,
    conversation: ConversationDocument,
    language: LanguageTag,
    last_question: MessageDocument | None,
) -> WidgetHandoffTarget:
    """Urgent: the visitor has waited already."""

    return WidgetHandoffTarget(
        business_id=business.id,
        conversation_id=conversation.id,
        contact_id=conversation.contact_id,
        language=language,
        summary=CodedHandoffSummary(
            code=HandoffSummaryCode.MODEL_UNAVAILABLE,
            quoted_text=(
                None
                if last_question is None
                else HandoffQuotedText(
                    str(last_question.text)[:MAX_QUOTED_MESSAGE_LENGTH] or "…"
                )
            ),
        ),
        is_already_handed_off=conversation.status is ConversationStatus.HANDOFF,
        reason=HandoffReason.NON_STANDARD_REQUEST,
        urgency=HandoffUrgency.HIGH,
    )
