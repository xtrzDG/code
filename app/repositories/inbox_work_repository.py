"""The open handoffs and requests behind a page of the team inbox."""

from collections.abc import Sequence

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.inbox_repositories import InboxWorkRepoContract
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    field_among,
    field_equals,
    of_business,
    stored_text,
)
from app.schemas.constants.bookings import LeadStatus
from app.schemas.constants.handoffs import HandoffStatus
from app.schemas.domain.bookings import LeadDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.storage_aggregates import DocumentAggregation
from app.schemas.dto.storage_pages import DocumentLatestQuery
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.inbox.booleans import HasOpenRequest
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

CONVERSATION_ID_FIELD: DocumentFieldPath = DocumentFieldPath("conversation_id")
STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
OPEN_HANDOFF_STATUSES: tuple[HandoffStatus, ...] = tuple(
    status for status in HandoffStatus if status is not HandoffStatus.RESOLVED
)
# A request waits for the team while it is new or someone works on it.
OPEN_REQUEST_STATUSES: tuple[LeadStatus, ...] = (
    LeadStatus.NEW,
    LeadStatus.IN_PROGRESS,
)


class InboxWorkRepository(InboxWorkRepoContract):
    """
    One `latest_by` statement per page for each kind of work (an indexed
    probe per conversation on `(business_id, doc_conversation_id)`, 1042),
    and one indexed count to recount a conversation's open requests.
    """

    def __init__(
        self,
        handoff_collection: DocumentCollectionAdapterContract[HandoffDocument],
        lead_collection: DocumentCollectionAdapterContract[LeadDocument],
    ) -> None:
        self._handoffs: DocumentCollectionAdapterContract[HandoffDocument] = (
            handoff_collection
        )
        self._leads: DocumentCollectionAdapterContract[LeadDocument] = lead_collection

    def latest_open_handoffs(
        self,
        business_id: BusinessId,
        conversation_ids: Sequence[ConversationId],
    ) -> dict[ConversationId, HandoffDocument]:
        if not conversation_ids:
            return {}

        return {
            handoff.conversation_id: handoff
            for handoff in self._handoffs.latest_by(
                latest_open(business_id, conversation_ids, OPEN_HANDOFF_STATUSES)
            )
        }

    def latest_open_requests(
        self,
        business_id: BusinessId,
        conversation_ids: Sequence[ConversationId],
    ) -> dict[ConversationId, LeadDocument]:
        if not conversation_ids:
            return {}

        return {
            lead.conversation_id: lead
            for lead in self._leads.latest_by(
                latest_open(business_id, conversation_ids, OPEN_REQUEST_STATUSES)
            )
            if lead.conversation_id is not None
        }

    def has_open_request(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> HasOpenRequest:
        groups = self._leads.count_by(
            DocumentAggregation(
                where=DocumentFilter(
                    matches=(
                        of_business(business_id),
                        field_equals(CONVERSATION_ID_FIELD, conversation_id),
                    ),
                    among=(field_among(STATUS_FIELD, OPEN_REQUEST_STATUSES),),
                )
            )
        )
        return any(int(group.count) > 0 for group in groups)


def latest_open(
    business_id: BusinessId,
    conversation_ids: Sequence[ConversationId],
    statuses: Sequence[object],
) -> DocumentLatestQuery:
    return DocumentLatestQuery(
        where=DocumentFilter(
            matches=(of_business(business_id),),
            among=(field_among(STATUS_FIELD, statuses),),
        ),
        group_field=CONVERSATION_ID_FIELD,
        groups=tuple(
            stored_text(conversation_id) for conversation_id in conversation_ids
        ),
        sort_field=CREATED_AT_FIELD,
    )
