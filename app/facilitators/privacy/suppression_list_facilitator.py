from collections.abc import Callable, Sequence

from typed_time_provider import Microseconds

from app.contracts.privacy import SuppressionListContract
from app.contracts.repositories.privacy_repositories import (
    SuppressionEntryRepoContract,
)
from app.schemas.domain.suppression import SuppressionEntryDocument
from app.schemas.dto.privacy.suppression import SuppressedIdentity
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.privacy.booleans import IsMessagingSuppressed
from app.schemas.typings.privacy.constrained_integers import SuppressedIdentityCount
from app.schemas.typings.privacy.constrained_strings import SuppressionDigest
from app.schemas.typings.privacy.prefixed_id import SuppressionEntryId
from app.utilities.privacy.suppression_digests import (
    erasure_entry_id,
    suppression_digest,
    suppression_entry_id,
)

type EntryIdOf = Callable[[BusinessId, SuppressionDigest], SuppressionEntryId]


class SuppressionListFacilitator(SuppressionListContract):
    """
    The suppression list over its entries: each identity is hashed with the
    platform's key (`suppression_digests`) into an entry whose id derives
    from the business and the digest, so adding is idempotent and a check
    of all of a customer's identities is one read by id. An erased
    customer's digests are erasure entries in the same collection under
    ids of their own (`erasure_entry_id`), so the STOP checks never read
    them.
    """

    def __init__(
        self,
        suppression_entry_repo: SuppressionEntryRepoContract,
        suppression_key: bytes,
    ) -> None:
        self._suppression_entry_repo: SuppressionEntryRepoContract = (
            suppression_entry_repo
        )
        self._suppression_key: bytes = suppression_key

    def suppress(
        self,
        business_id: BusinessId,
        identities: Sequence[SuppressedIdentity],
        now: Microseconds,
    ) -> SuppressedIdentityCount:
        added: int = 0
        for identity in dict.fromkeys(identities):
            digest: SuppressionDigest = suppression_digest(
                self._suppression_key, business_id, identity
            )
            if self._suppression_entry_repo.insert_if_new(
                SuppressionEntryDocument(
                    id=suppression_entry_id(business_id, digest),
                    business_id=business_id,
                    identity_digest=digest,
                    channel=identity.channel,
                    created_at=now,
                    updated_at=now,
                )
            ):
                added += 1

        return SuppressedIdentityCount(added)

    def lift(
        self,
        business_id: BusinessId,
        identities: Sequence[SuppressedIdentity],
    ) -> SuppressedIdentityCount:
        listed: list[SuppressionEntryDocument] = self._suppression_entry_repo.get_many(
            business_id, self._entry_ids(business_id, identities)
        )
        for entry in listed:
            self._suppression_entry_repo.delete(business_id, entry.id)

        return SuppressedIdentityCount(len(listed))

    def is_suppressed(
        self,
        business_id: BusinessId,
        identities: Sequence[SuppressedIdentity],
    ) -> IsMessagingSuppressed:
        if not identities:
            return False

        return bool(
            self._suppression_entry_repo.get_many(
                business_id, self._entry_ids(business_id, identities)
            )
        )

    def remember_erasure(
        self,
        business_id: BusinessId,
        identities: Sequence[SuppressedIdentity],
        now: Microseconds,
    ) -> SuppressedIdentityCount:
        added: int = 0
        for identity in dict.fromkeys(identities):
            digest: SuppressionDigest = suppression_digest(
                self._suppression_key, business_id, identity
            )
            entry = SuppressionEntryDocument(
                id=erasure_entry_id(business_id, digest),
                business_id=business_id,
                identity_digest=digest,
                channel=identity.channel,
                created_at=now,
                updated_at=now,
            )
            if self._suppression_entry_repo.insert_if_new(entry):
                added += 1
            else:
                # Erased again: the entry dates from the latest erasure.
                self._suppression_entry_repo.delete(business_id, entry.id)
                self._suppression_entry_repo.insert_if_new(entry)

        return SuppressedIdentityCount(added)

    def erased_at(
        self,
        business_id: BusinessId,
        identities: Sequence[SuppressedIdentity],
    ) -> Microseconds | None:
        if not identities:
            return None

        entries: list[SuppressionEntryDocument] = self._suppression_entry_repo.get_many(
            business_id,
            self._entry_ids(business_id, identities, erasure_entry_id),
        )
        if not entries:
            return None

        return Microseconds(max(int(entry.created_at) for entry in entries))

    def _entry_ids(
        self,
        business_id: BusinessId,
        identities: Sequence[SuppressedIdentity],
        entry_id_of: EntryIdOf = suppression_entry_id,
    ) -> list[SuppressionEntryId]:
        return list(
            dict.fromkeys(
                entry_id_of(
                    business_id,
                    suppression_digest(self._suppression_key, business_id, identity),
                )
                for identity in identities
            )
        )
