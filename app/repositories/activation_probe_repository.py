from collections.abc import Callable

from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.setup_repositories import ActivationProbeRepoContract
from app.repositories.document_queries import of_business
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit

# How many of a business's earliest documents a probe reads. Test chats and
# automatic checks come before the first real customer, and owners rarely
# run more than a few dozen; the read stays small even for a business with
# years of history, because it walks the (business_id, created_at) index.
PROBE_LIMIT: DocumentQueryLimit = DocumentQueryLimit(200)


class ActivationProbeRepository(ActivationProbeRepoContract):
    """
    Finds when a business first had a real conversation, booking or
    handoff, skipping the sandbox ones of the test chat and the automatic
    checks. Each probe reads at most PROBE_LIMIT of the business's earliest
    documents, in write order, through the business index.
    """

    def __init__(
        self,
        conversation_collection: DocumentCollectionAdapterContract[
            ConversationDocument
        ],
        booking_collection: DocumentCollectionAdapterContract[BookingDocument],
        handoff_collection: DocumentCollectionAdapterContract[HandoffDocument],
    ) -> None:
        self._conversation_collection: DocumentCollectionAdapterContract[
            ConversationDocument
        ] = conversation_collection
        self._booking_collection: DocumentCollectionAdapterContract[
            BookingDocument
        ] = booking_collection
        self._handoff_collection: DocumentCollectionAdapterContract[
            HandoffDocument
        ] = handoff_collection

    def find_first_real_conversation_at(
        self, business_id: BusinessId
    ) -> Microseconds | None:
        return find_first_at(
            self._conversation_collection,
            business_id,
            lambda conversation: not conversation.is_sandbox
            and conversation.channel is not ChannelKind.OWNER_TEST,
        )

    def find_first_real_booking_at(self, business_id: BusinessId) -> Microseconds | None:
        return find_first_at(
            self._booking_collection,
            business_id,
            lambda booking: not booking.is_sandbox,
        )

    def find_first_real_handoff_at(self, business_id: BusinessId) -> Microseconds | None:
        return find_first_at(
            self._handoff_collection,
            business_id,
            lambda handoff: not handoff.is_sandbox,
        )


def find_first_at[Probed: BaseDocument](
    collection: DocumentCollectionAdapterContract[Probed],
    business_id: BusinessId,
    is_real: Callable[[Probed], bool],
) -> Microseconds | None:
    """Creation time of the business's earliest real document, if any."""

    times: list[Microseconds] = [
        document.created_at
        for document in collection.list_by_fields(
            [of_business(business_id)], limit=PROBE_LIMIT
        )
        if is_real(document)
    ]
    return min(times, default=None)
