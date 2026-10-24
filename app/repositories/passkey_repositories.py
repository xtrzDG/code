from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.passkey_repositories import (
    PasskeyChallengeRepoContract,
    PasskeyRepoContract,
)
from app.repositories.document_queries import field_equals, time_range
from app.schemas.domain.passkeys import PasskeyChallengeDocument, PasskeyDocument
from app.schemas.typings.passkeys.constrained_integers import (
    PasskeyCount,
    WebAuthnSignCount,
)
from app.schemas.typings.passkeys.constrained_strings import PasskeyName
from app.schemas.typings.passkeys.prefixed_id import PasskeyChallengeId, PasskeyId
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.users.prefixed_id import UserId

USER_ID_FIELD: DocumentFieldPath = DocumentFieldPath("user_id")
CREATED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("created_at")


class PasskeyRepository(PasskeyRepoContract):
    """
    Passkeys under their id, derived from the credential id
    (`passkey_identity.passkey_id_for`): adding one is `insert_if_absent`,
    so a credential is stored once even when two requests race.
    """

    def __init__(
        self, collection: DocumentCollectionAdapterContract[PasskeyDocument]
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[PasskeyDocument] = (
            collection
        )

    def list_for_user(self, user_id: UserId) -> list[PasskeyDocument]:
        passkeys: list[PasskeyDocument] = self._collection.list_by_fields(
            [field_equals(USER_ID_FIELD, user_id)]
        )
        return sorted(passkeys, key=lambda passkey: -int(passkey.created_at))

    def count_for_user(self, user_id: UserId) -> PasskeyCount:
        return PasskeyCount(
            int(
                self._collection.count_by_fields([field_equals(USER_ID_FIELD, user_id)])
            )
        )

    def get(self, passkey_id: PasskeyId) -> PasskeyDocument | None:
        return self._collection.get(str(passkey_id))

    def add(self, passkey: PasskeyDocument) -> bool:
        return bool(self._collection.insert_if_absent(str(passkey.id), passkey))

    def record_use(
        self,
        passkey_id: PasskeyId,
        expected_sign_count: WebAuthnSignCount,
        sign_count: WebAuthnSignCount,
        now: Microseconds,
    ) -> PasskeyDocument | None:
        def remember(passkey: PasskeyDocument) -> PasskeyDocument | None:
            if (
                passkey.clone_suspected_at is not None
                or passkey.sign_count != expected_sign_count
            ):
                return None

            passkey.sign_count = sign_count
            passkey.last_used_at = now
            passkey.updated_at = now
            return passkey

        return self._collection.modify(str(passkey_id), remember)

    def mark_clone_suspected(
        self, passkey_id: PasskeyId, now: Microseconds
    ) -> PasskeyDocument | None:
        def suspend(passkey: PasskeyDocument) -> PasskeyDocument | None:
            if passkey.clone_suspected_at is None:
                passkey.clone_suspected_at = now
                passkey.updated_at = now
            return passkey

        return self._collection.modify(str(passkey_id), suspend)

    def rename(
        self, passkey_id: PasskeyId, name: PasskeyName, now: Microseconds
    ) -> PasskeyDocument | None:
        def change_name(passkey: PasskeyDocument) -> PasskeyDocument | None:
            passkey.name = name
            passkey.updated_at = now
            return passkey

        return self._collection.modify(str(passkey_id), change_name)

    def delete(self, passkey_id: PasskeyId) -> bool:
        if self._collection.get(str(passkey_id)) is None:
            return False

        self._collection.delete(str(passkey_id))
        return True


class PasskeyChallengeRepository(PasskeyChallengeRepoContract):
    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[PasskeyChallengeDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            PasskeyChallengeDocument
        ] = collection

    def save(self, challenge: PasskeyChallengeDocument) -> None:
        self._collection.upsert(str(challenge.id), challenge)

    def get(self, challenge_id: PasskeyChallengeId) -> PasskeyChallengeDocument | None:
        return self._collection.get(str(challenge_id))

    def consume(
        self, challenge_id: PasskeyChallengeId, now: Microseconds
    ) -> PasskeyChallengeDocument | None:
        def mark_consumed(
            challenge: PasskeyChallengeDocument,
        ) -> PasskeyChallengeDocument | None:
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
