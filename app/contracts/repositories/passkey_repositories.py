"""
Persistence contracts of passkeys: a person's passkeys and the challenges
of passkey ceremonies (platform-wide collections, migration 1201).

Implementations return independent copies: mutating a returned document
does not change stored state until it is saved.
"""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.passkeys import PasskeyChallengeDocument, PasskeyDocument
from app.schemas.typings.passkeys.constrained_integers import (
    PasskeyCount,
    WebAuthnSignCount,
)
from app.schemas.typings.passkeys.constrained_strings import PasskeyName
from app.schemas.typings.passkeys.prefixed_id import PasskeyChallengeId, PasskeyId
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.users.prefixed_id import UserId


class PasskeyRepoContract(RepoContract, Protocol):
    """
    A person's passkeys, each stored under an id derived from its
    credential id: one credential is one passkey, whoever adds it.
    """

    def list_for_user(self, user_id: UserId) -> list[PasskeyDocument]:
        """The person's passkeys, newest first (indexed by user)."""
        raise NotImplementedError

    def count_for_user(self, user_id: UserId) -> PasskeyCount:
        raise NotImplementedError

    def get(self, passkey_id: PasskeyId) -> PasskeyDocument | None:
        raise NotImplementedError

    def add(self, passkey: PasskeyDocument) -> bool:
        """
        Store a new passkey in one atomic step: False, and nothing written,
        when its credential is already stored (for anyone).
        """
        raise NotImplementedError

    def record_use(
        self,
        passkey_id: PasskeyId,
        expected_sign_count: WebAuthnSignCount,
        sign_count: WebAuthnSignCount,
        now: Microseconds,
    ) -> PasskeyDocument | None:
        """
        Remember an accepted use (compare-and-swap): only while the stored
        counter is still `expected_sign_count` and the passkey is not
        suspected of a copy. None, and nothing written, when a parallel use
        came first or the passkey is gone or suspended.
        """
        raise NotImplementedError

    def mark_clone_suspected(
        self, passkey_id: PasskeyId, now: Microseconds
    ) -> PasskeyDocument | None:
        """
        Stop a passkey whose counter went backwards: it signs nothing more
        (the first mark is kept). None when it is gone.
        """
        raise NotImplementedError

    def rename(
        self, passkey_id: PasskeyId, name: PasskeyName, now: Microseconds
    ) -> PasskeyDocument | None:
        raise NotImplementedError

    def delete(self, passkey_id: PasskeyId) -> bool:
        """False when it was already gone."""
        raise NotImplementedError


class PasskeyChallengeRepoContract(RepoContract, Protocol):
    def save(self, challenge: PasskeyChallengeDocument) -> None:
        raise NotImplementedError

    def get(self, challenge_id: PasskeyChallengeId) -> PasskeyChallengeDocument | None:
        raise NotImplementedError

    def consume(
        self, challenge_id: PasskeyChallengeId, now: Microseconds
    ) -> PasskeyChallengeDocument | None:
        """
        Mark the challenge consumed (compare-and-swap): the consumed
        challenge, or None when another request consumed it first or it is
        missing.
        """
        raise NotImplementedError

    def delete_created_before(self, created_before: Microseconds) -> DocumentCount:
        """Purge challenges created before a moment; returns how many."""
        raise NotImplementedError
