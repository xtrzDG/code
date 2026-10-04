from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.mfa_repositories import (
    MfaChallengeRepoContract,
    RecoveryCodeRepoContract,
    TotpFactorRepoContract,
)
from app.repositories.document_queries import field_equals, time_range
from app.schemas.constants.mfa import TotpFactorStatus
from app.schemas.domain.mfa import (
    MfaChallengeDocument,
    RecoveryCodeDocument,
    TotpFactorDocument,
)
from app.schemas.dto.storage_pages import DocumentPagePosition, DocumentPageQuery
from app.schemas.typings.mfa.constrained_integers import MfaAttemptCount, TotpTimeStep
from app.schemas.typings.mfa.prefixed_id import MfaChallengeId, RecoveryCodeId
from app.schemas.typings.mfa.strings import SealedTotpSecret
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentQueryLimit,
)
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger
from app.schemas.typings.storage.strings import StoredDocumentKey
from app.schemas.typings.users.prefixed_id import UserId

USER_ID_FIELD: DocumentFieldPath = DocumentFieldPath("user_id")
CREATED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("created_at")
# Factors the key rotation re-seals per storage read.
FACTOR_BATCH_SIZE: DocumentQueryLimit = DocumentQueryLimit(200)


class TotpFactorRepository(TotpFactorRepoContract):
    """Authenticators stored under their user's id: one per user."""

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[TotpFactorDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[TotpFactorDocument] = (
            collection
        )

    def get_for_user(self, user_id: UserId) -> TotpFactorDocument | None:
        return self._collection.get(str(user_id))

    def start_enrollment(self, factor: TotpFactorDocument) -> bool:
        key: str = str(factor.user_id)
        if self._collection.insert_if_absent(key, factor):
            return True

        return self._collection.replace_if(
            key,
            factor,
            lambda stored: stored.status is TotpFactorStatus.PENDING,
        )

    def activate(
        self, user_id: UserId, step: TotpTimeStep, now: Microseconds
    ) -> TotpFactorDocument | None:
        def confirm(factor: TotpFactorDocument) -> TotpFactorDocument | None:
            if factor.status is not TotpFactorStatus.PENDING:
                return None

            factor.status = TotpFactorStatus.ACTIVE
            factor.confirmed_at = now
            factor.last_used_step = step
            factor.last_used_at = now
            factor.updated_at = now
            return factor

        return self._collection.modify(str(user_id), confirm)

    def record_use(
        self, user_id: UserId, step: TotpTimeStep, now: Microseconds
    ) -> TotpFactorDocument | None:
        def remember(factor: TotpFactorDocument) -> TotpFactorDocument | None:
            if factor.status is not TotpFactorStatus.ACTIVE:
                return None

            if factor.last_used_step is not None and step <= factor.last_used_step:
                return None

            factor.last_used_step = step
            factor.last_used_at = now
            factor.updated_at = now
            return factor

        return self._collection.modify(str(user_id), remember)

    def replace_sealed_secret(
        self,
        user_id: UserId,
        expected: SealedTotpSecret,
        resealed: SealedTotpSecret,
        now: Microseconds,
    ) -> bool:
        def reseal(factor: TotpFactorDocument) -> TotpFactorDocument | None:
            if factor.sealed_secret != expected:
                return None

            factor.sealed_secret = resealed
            factor.updated_at = now
            return factor

        return self._collection.modify(str(user_id), reseal) is not None

    def delete_for_user(self, user_id: UserId) -> None:
        self._collection.delete(str(user_id))

    def list_after(self, after: TotpFactorDocument | None) -> list[TotpFactorDocument]:
        return self._collection.page_by(
            DocumentPageQuery(
                sort_fields=(CREATED_AT_FIELD,),
                is_descending=False,
                after=None
                if after is None
                else DocumentPagePosition(
                    values=(DocumentFieldInteger(int(after.created_at)),),
                    document_key=StoredDocumentKey(str(after.user_id)),
                ),
                limit=FACTOR_BATCH_SIZE,
            )
        )


class RecoveryCodeRepository(RecoveryCodeRepoContract):
    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[RecoveryCodeDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[RecoveryCodeDocument] = (
            collection
        )

    def list_for_user(self, user_id: UserId) -> list[RecoveryCodeDocument]:
        return self._collection.list_by_fields([field_equals(USER_ID_FIELD, user_id)])

    def replace_for_user(
        self, user_id: UserId, codes: Sequence[RecoveryCodeDocument]
    ) -> None:
        self.delete_for_user(user_id)
        self._collection.upsert_many([(str(code.id), code) for code in codes])

    def spend(
        self, code_id: RecoveryCodeId, now: Microseconds
    ) -> RecoveryCodeDocument | None:
        def mark_used(code: RecoveryCodeDocument) -> RecoveryCodeDocument | None:
            if code.used_at is not None:
                return None

            code.used_at = now
            code.updated_at = now
            return code

        return self._collection.modify(str(code_id), mark_used)

    def delete_for_user(self, user_id: UserId) -> None:
        for code in self.list_for_user(user_id):
            self._collection.delete(str(code.id))


class MfaChallengeRepository(MfaChallengeRepoContract):
    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[MfaChallengeDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[MfaChallengeDocument] = (
            collection
        )

    def save(self, challenge: MfaChallengeDocument) -> None:
        self._collection.upsert(str(challenge.id), challenge)

    def get(self, challenge_id: MfaChallengeId) -> MfaChallengeDocument | None:
        return self._collection.get(str(challenge_id))

    def register_failed_attempt(
        self,
        challenge_id: MfaChallengeId,
        max_failed_attempts: MfaAttemptCount,
        now: Microseconds,
    ) -> MfaAttemptCount | None:
        def count_attempt(
            challenge: MfaChallengeDocument,
        ) -> MfaChallengeDocument | None:
            if challenge.is_consumed or challenge.failed_attempts >= int(
                max_failed_attempts
            ):
                return None

            challenge.failed_attempts = MfaAttemptCount(challenge.failed_attempts + 1)
            challenge.updated_at = now
            return challenge

        counted: MfaChallengeDocument | None = self._collection.modify(
            str(challenge_id), count_attempt
        )
        return None if counted is None else counted.failed_attempts

    def consume(
        self, challenge_id: MfaChallengeId, now: Microseconds
    ) -> MfaChallengeDocument | None:
        def mark_consumed(
            challenge: MfaChallengeDocument,
        ) -> MfaChallengeDocument | None:
            if challenge.is_consumed:
                return None

            challenge.is_consumed = True
            challenge.updated_at = now
            return challenge

        return self._collection.modify(str(challenge_id), mark_consumed)

    def delete_created_before(self, created_before: Microseconds) -> DocumentCount:
        return self._collection.delete_by_range(
            time_range(CREATED_AT_FIELD, ending_before=created_before)
        )
