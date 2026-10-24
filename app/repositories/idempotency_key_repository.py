from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.idempotency_repositories import (
    IdempotencyKeyRepoContract,
)
from app.repositories.document_queries import time_range
from app.schemas.constants.idempotency import IdempotencyRecordStatus
from app.schemas.domain.idempotency_keys import IdempotencyKeyDocument
from app.schemas.dto.idempotency import StoredResponse
from app.schemas.typings.idempotency.prefixed_id import (
    IdempotencyClaimId,
    IdempotencyRecordId,
)
from app.schemas.typings.storage.booleans import IsDocumentInserted
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.utilities.idempotency.idempotency_records import is_free

EXPIRES_AT_FIELD: DocumentFieldPath = DocumentFieldPath("expires_at")


class IdempotencyKeyRepository(IdempotencyKeyRepoContract):
    """
    Idempotency key records (a platform collection, 1174), read by the id
    derived from the user and the key. Every change of a record is one
    atomic step of the storage (an insert that fails on a taken id, or a
    row-locked read-and-write), so two requests with the same key never
    both hold it; the purge deletes expired records by `expires_at`
    (indexed).
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[IdempotencyKeyDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[IdempotencyKeyDocument] = (
            collection
        )

    def insert_if_new(self, record: IdempotencyKeyDocument) -> IsDocumentInserted:
        return self._collection.insert_if_absent(str(record.id), record)

    def get(self, record_id: IdempotencyRecordId) -> IdempotencyKeyDocument | None:
        return self._collection.get(str(record_id))

    def take_over_if_free(
        self, record: IdempotencyKeyDocument, now: Microseconds
    ) -> bool:
        return self._collection.replace_if(
            str(record.id), record, lambda stored: is_free(stored, now)
        )

    def complete(
        self,
        record_id: IdempotencyRecordId,
        claim_id: IdempotencyClaimId,
        response: StoredResponse,
        now: Microseconds,
    ) -> IdempotencyKeyDocument | None:
        def store_answer(
            stored: IdempotencyKeyDocument,
        ) -> IdempotencyKeyDocument | None:
            if not is_held_by(stored, claim_id, now):
                return None

            return stored.model_copy(
                update={
                    "status": IdempotencyRecordStatus.COMPLETED,
                    "response_status": response.status,
                    "response_media_type": response.media_type,
                    "response_body": response.body,
                    "completed_at": now,
                    "updated_at": now,
                }
            )

        return self._collection.modify(str(record_id), store_answer)

    def release(
        self,
        record_id: IdempotencyRecordId,
        claim_id: IdempotencyClaimId,
        now: Microseconds,
    ) -> IdempotencyKeyDocument | None:
        def expire(stored: IdempotencyKeyDocument) -> IdempotencyKeyDocument | None:
            if not is_held_by(stored, claim_id, now):
                return None

            return stored.model_copy(
                update={"expires_at": now, "lease_expires_at": now, "updated_at": now}
            )

        return self._collection.modify(str(record_id), expire)

    def delete_expired_before(self, moment: Microseconds) -> DocumentCount:
        return self._collection.delete_by_range(
            time_range(EXPIRES_AT_FIELD, ending_before=moment)
        )


def is_held_by(
    record: IdempotencyKeyDocument, claim_id: IdempotencyClaimId, now: Microseconds
) -> bool:
    """
    The request of `claim_id` still holds the key: its claim was neither
    taken over, released nor completed. A request that outlived its lease
    still finishes while nobody took the key over.
    """

    return (
        record.claim_id == claim_id
        and record.status is IdempotencyRecordStatus.IN_PROGRESS
        and int(record.expires_at) > int(now)
    )
