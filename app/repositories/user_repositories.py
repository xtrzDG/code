from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.user_repositories import (
    OtpChallengeRepoContract,
    UserRepoContract,
    UserSessionRepoContract,
)
from app.repositories.document_queries import time_range
from app.schemas.domain.users import (
    OtpChallengeDocument,
    UserDocument,
    UserSessionDocument,
)
from app.schemas.dto.storage_queries import DocumentFieldRange
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger
from app.schemas.typings.storage.strings import DocumentFieldText
from app.schemas.typings.users.constrained_integers import OtpAttemptCount
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import (
    OtpChallengeId,
    UserId,
    UserSessionId,
)
from app.schemas.typings.users.strings import AccessTokenHash

PHONE_NUMBER_FIELD: DocumentFieldPath = DocumentFieldPath("phone_number")
EMAIL_FIELD: DocumentFieldPath = DocumentFieldPath("email")
CREATED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("created_at")
TOKEN_HASH_FIELD: DocumentFieldPath = DocumentFieldPath("token_hash")
EXPIRES_AT_FIELD: DocumentFieldPath = DocumentFieldPath("expires_at")


class UserRepository(UserRepoContract):
    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[UserDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[UserDocument] = collection

    def save(self, user: UserDocument) -> None:
        self._collection.upsert(str(user.id), user)

    def get(self, user_id: UserId) -> UserDocument | None:
        return self._collection.get(str(user_id))

    def find_by_phone_number(
        self,
        phone_number: E164PhoneNumber,
    ) -> UserDocument | None:
        return self._collection.find_one_by_field(
            PHONE_NUMBER_FIELD, DocumentFieldText(str(phone_number))
        )

    def find_by_email(self, email: EmailAddress) -> UserDocument | None:
        return self._collection.find_one_by_field(
            EMAIL_FIELD, DocumentFieldText(str(email))
        )


class OtpChallengeRepository(OtpChallengeRepoContract):
    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[OtpChallengeDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[OtpChallengeDocument] = (
            collection
        )

    def save(self, challenge: OtpChallengeDocument) -> None:
        self._collection.upsert(str(challenge.id), challenge)

    def get(self, challenge_id: OtpChallengeId) -> OtpChallengeDocument | None:
        return self._collection.get(str(challenge_id))

    def list_created_since(
        self,
        created_after: Microseconds,
    ) -> list[OtpChallengeDocument]:
        return self._collection.list_by_range(
            DocumentFieldRange(
                field=CREATED_AT_FIELD,
                lower=DocumentFieldInteger(int(created_after) + 1),
            )
        )

    def register_failed_attempt(
        self,
        challenge_id: OtpChallengeId,
        max_failed_attempts: OtpAttemptCount,
        now: Microseconds,
    ) -> OtpAttemptCount | None:
        def count_attempt(
            challenge: OtpChallengeDocument,
        ) -> OtpChallengeDocument | None:
            if challenge.is_consumed or challenge.failed_attempts >= int(
                max_failed_attempts
            ):
                return None

            challenge.failed_attempts = OtpAttemptCount(challenge.failed_attempts + 1)
            challenge.updated_at = now
            return challenge

        counted: OtpChallengeDocument | None = self._collection.modify(
            str(challenge_id), count_attempt
        )
        return None if counted is None else counted.failed_attempts

    def consume(
        self,
        challenge_id: OtpChallengeId,
        now: Microseconds,
    ) -> OtpChallengeDocument | None:
        def mark_consumed(
            challenge: OtpChallengeDocument,
        ) -> OtpChallengeDocument | None:
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

    def delete(self, challenge_id: OtpChallengeId) -> None:
        self._collection.delete(str(challenge_id))


class UserSessionRepository(UserSessionRepoContract):
    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[UserSessionDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[UserSessionDocument] = (
            collection
        )

    def save(self, session: UserSessionDocument) -> None:
        self._collection.upsert(str(session.id), session)

    def find_by_token_hash(
        self,
        token_hash: AccessTokenHash,
    ) -> UserSessionDocument | None:
        return self._collection.find_one_by_field(
            TOKEN_HASH_FIELD, DocumentFieldText(str(token_hash))
        )

    def delete_expired(self, now: Microseconds) -> DocumentCount:
        # A session is valid while now < expires_at (AuthenticateUserUseCase).
        return self._collection.delete_by_range(
            DocumentFieldRange(
                field=EXPIRES_AT_FIELD,
                upper=DocumentFieldInteger(int(now) + 1),
            )
        )

    def delete(self, session_id: UserSessionId) -> None:
        self._collection.delete(str(session_id))
