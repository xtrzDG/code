"""Handoffs and unanswered questions rendered for the cabinet."""

from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.dto.handoffs import UnansweredQuestionView
from app.schemas.dto.operations.handoffs import HandoffListItem
from app.schemas.dto.operations.unanswered_questions import UnansweredQuestionDetails


def build_handoff_list_item(
    handoff: HandoffDocument,
    contact: ContactDocument | None,
) -> HandoffListItem:
    return HandoffListItem(
        id=handoff.id,
        business_id=handoff.business_id,
        conversation_id=handoff.conversation_id,
        contact_id=handoff.contact_id,
        contact_name=None if contact is None else contact.name,
        contact_phone_number=None if contact is None else contact.phone_number,
        reason=handoff.reason,
        summary=handoff.summary,
        summary_code=handoff.summary_code,
        quoted_text=handoff.quoted_text,
        flagged_values=list(handoff.flagged_values),
        urgency=handoff.urgency,
        status=handoff.status,
        is_sandbox=handoff.is_sandbox,
        created_at=handoff.created_at,
        resolved_at=handoff.resolved_at,
    )


def build_unanswered_question_view(
    question: UnansweredQuestionDocument,
) -> UnansweredQuestionView:
    return UnansweredQuestionView(
        id=question.id,
        business_id=question.business_id,
        question=question.question,
        language=question.language,
    )


def build_unanswered_question_details(
    question: UnansweredQuestionDocument,
) -> UnansweredQuestionDetails:
    return UnansweredQuestionDetails(
        id=question.id,
        business_id=question.business_id,
        question=question.question,
        language=question.language,
        occurrence_count=question.occurrence_count,
        last_seen_at=question.last_seen_at,
        is_resolved=question.is_resolved,
        resolved_knowledge_item_id=question.resolved_knowledge_item_id,
        is_sandbox=question.is_sandbox,
    )
