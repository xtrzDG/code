"""
The admin's client care (migration 1143): the credit ledger and the
platform team's notes, read per business; the changes of a client's
health, newest first per business and by status across businesses; and
how far each digest of the team has looked.
"""

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.client_care_repositories import (
    AdminDigestStateRepoContract,
    BillingCreditRepoContract,
    ClientHealthChangeRepoContract,
    ClientNoteRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import field_equals, of_business, time_range
from app.schemas.constants.client_health import AdminDigestKind, ClientHealthStatus
from app.schemas.domain.billing_credits import BillingCreditDocument
from app.schemas.domain.client_health_changes import (
    AdminDigestStateDocument,
    ClientHealthChangeDocument,
)
from app.schemas.domain.client_notes import ClientNoteDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.client_health.prefixed_id import ClientNoteId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

CHANGED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("changed_at")
STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
# A range needs a bound: the first page of a client's changes reads from
# the beginning of time.
EPOCH: Microseconds = Microseconds(0)


class BillingCreditRepository(
    BusinessScopedRepository[BillingCreditDocument], BillingCreditRepoContract
):
    """Ledger lines keyed by id; a used line's id derives from its invoice."""

    def record(self, line: BillingCreditDocument) -> bool:
        return bool(self._collection.insert_if_absent(str(line.id), line))

    def list_by_business(self, business_id: BusinessId) -> list[BillingCreditDocument]:
        return self._list_in_business(business_id)


class ClientNoteRepository(
    BusinessScopedRepository[ClientNoteDocument], ClientNoteRepoContract
):
    """The platform team's notes about a client, keyed by note id."""

    def save(self, note: ClientNoteDocument) -> None:
        self._store(str(note.id), note)

    def get(
        self, business_id: BusinessId, note_id: ClientNoteId
    ) -> ClientNoteDocument | None:
        return self._load(business_id, str(note_id))

    def delete(self, business_id: BusinessId, note_id: ClientNoteId) -> None:
        self._remove(business_id, str(note_id))

    def list_by_business(
        self, business_id: BusinessId, limit: DocumentQueryLimit
    ) -> list[ClientNoteDocument]:
        return self._list_in_business(business_id, limit=limit)


class ClientHealthChangeRepository(
    BusinessScopedRepository[ClientHealthChangeDocument],
    ClientHealthChangeRepoContract,
):
    """Health changes by time within a client and by status across clients."""

    def add(self, change: ClientHealthChangeDocument) -> None:
        self._store(str(change.id), change)

    def list_before(
        self,
        business_id: BusinessId,
        before: Microseconds | None,
        limit: DocumentQueryLimit,
    ) -> list[ClientHealthChangeDocument]:
        return self._collection.list_by_range(
            time_range(CHANGED_AT_FIELD, starting_at=EPOCH, ending_before=before),
            (of_business(business_id),),
            is_descending=True,
            limit=limit,
        )

    def list_changes_to(
        self,
        status: ClientHealthStatus,
        changed_from: Microseconds,
        changed_before: Microseconds,
    ) -> list[ClientHealthChangeDocument]:
        return self._collection.list_by_range(
            time_range(
                CHANGED_AT_FIELD,
                starting_at=changed_from,
                ending_before=changed_before,
            ),
            (field_equals(STATUS_FIELD, status),),
        )


class AdminDigestStateRepository(AdminDigestStateRepoContract):
    """How far each digest has looked (platform), keyed by its kind."""

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[AdminDigestStateDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            AdminDigestStateDocument
        ] = collection

    def get(self, kind: AdminDigestKind) -> AdminDigestStateDocument | None:
        return self._collection.get(kind.value)

    def save(self, state: AdminDigestStateDocument) -> None:
        self._collection.upsert(state.kind.value, state)
