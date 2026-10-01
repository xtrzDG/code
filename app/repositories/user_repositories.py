from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories import (
    OtpChallengeRepoContract,
    UserRepoContract,
    UserSessionRepoContract,
)
from app.schemas.domain.users import (
    OtpChallengeDocument,
    UserDocument,
    UserSessionDocument,
)
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import (
    OtpChallengeId,
    UserId,
    UserSessionId,
)
from app.schemas.typings.users.strings import AccessTokenHash


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
        for user in self._collection.list_all():
            if user.phone_number == phone_number:
                return user

        return None

    def find_by_email(self, email: EmailAddress) -> UserDocument | None:
        for user in self._collection.list_all():
            if user.email == email:
                return user

        return None


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
        return [
            challenge
            for challenge in self._collection.list_all()
            if challenge.created_at > created_after
        ]

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
        for session in self._collection.list_all():
            if session.token_hash == token_hash:
                return session

        return None

    def delete(self, session_id: UserSessionId) -> None:
        self._collection.delete(str(session_id))
