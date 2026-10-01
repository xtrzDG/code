from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories import (
    OtpChallengeRepoContract,
    OwnerRepoContract,
    OwnerSessionRepoContract,
)
from app.schemas.domain.owners import (
    OtpChallengeDocument,
    OwnerDocument,
    OwnerSessionDocument,
)
from app.schemas.typings.accounts.constrained_strings import EmailAddress
from app.schemas.typings.accounts.prefixed_id import (
    OtpChallengeId,
    OwnerId,
    OwnerSessionId,
)
from app.schemas.typings.accounts.strings import AccessTokenHash
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber


class OwnerRepository(OwnerRepoContract):
    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[OwnerDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[OwnerDocument] = collection

    def save(self, owner: OwnerDocument) -> None:
        self._collection.upsert(str(owner.id), owner)

    def get(self, owner_id: OwnerId) -> OwnerDocument | None:
        return self._collection.get(str(owner_id))

    def find_by_phone_number(
        self,
        phone_number: E164PhoneNumber,
    ) -> OwnerDocument | None:
        for owner in self._collection.list_all():
            if owner.phone_number == phone_number:
                return owner

        return None

    def find_by_email(self, email: EmailAddress) -> OwnerDocument | None:
        for owner in self._collection.list_all():
            if owner.email == email:
                return owner

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


class OwnerSessionRepository(OwnerSessionRepoContract):
    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[OwnerSessionDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[OwnerSessionDocument] = (
            collection
        )

    def save(self, session: OwnerSessionDocument) -> None:
        self._collection.upsert(str(session.id), session)

    def find_by_token_hash(
        self,
        token_hash: AccessTokenHash,
    ) -> OwnerSessionDocument | None:
        for session in self._collection.list_all():
            if session.token_hash == token_hash:
                return session

        return None

    def delete(self, session_id: OwnerSessionId) -> None:
        self._collection.delete(str(session_id))
