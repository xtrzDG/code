"""Persistence contract of the idempotency keys of creating requests (1174)."""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.idempotency_keys import IdempotencyKeyDocument
from app.schemas.dto.idempotency import StoredResponse
from app.schemas.typings.idempotency.prefixed_id import (
    IdempotencyClaimId,
    IdempotencyRecordId,
)
from app.schemas.typings.storage.booleans import IsDocumentInserted
from app.schemas.typings.storage.constrained_integers import DocumentCount


class IdempotencyKeyRepoContract(RepoContract, Protocol):
    def insert_if_new(self, record: IdempotencyKeyDocument) -> IsDocumentInserted:
        """
        Store a new record in one atomic step: False, and nothing written,
        when a record of that id exists, even one a concurrent request in
        another process has just written.
        """
        raise NotImplementedError

    def get(self, record_id: IdempotencyRecordId) -> IdempotencyKeyDocument | None:
        raise NotImplementedError

    def take_over_if_free(
        self, record: IdempotencyKeyDocument, now: Microseconds
    ) -> bool:
        """
        Overwrite the stored record of `record.id` with `record` only while
        it is free at `now` (expired or released, or a claim past its lease),
        in one step: False, and nothing written, when it is missing or held.
        Of two requests taking over the same record, one wins.
        """
        raise NotImplementedError

    def complete(
        self,
        record_id: IdempotencyRecordId,
        claim_id: IdempotencyClaimId,
        response: StoredResponse,
        now: Microseconds,
    ) -> IdempotencyKeyDocument | None:
        """
        Store the answer of the request holding the claim and mark the record
        COMPLETED, in one step; None, and nothing written, when the claim is
        no longer that request's (taken over, released, completed).
        """
        raise NotImplementedError

    def release(
        self,
        record_id: IdempotencyRecordId,
        claim_id: IdempotencyClaimId,
        now: Microseconds,
    ) -> IdempotencyKeyDocument | None:
        """
        Free the key of a request that did not succeed (the record expires
        at `now`), only while that request still holds it; None otherwise.
        """
        raise NotImplementedError

    def delete_expired_before(self, moment: Microseconds) -> DocumentCount:
        """Delete every record that expired before `moment` (the purge)."""
        raise NotImplementedError
