"""
Persistence contracts of two-factor sign-in: authenticators, recovery codes
and the second step of a sign-in (platform-wide collections).

Implementations return independent copies: mutating a returned document does
not change stored state until it is saved.
"""

from collections.abc import Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.mfa import (
    MfaChallengeDocument,
    RecoveryCodeDocument,
    TotpFactorDocument,
)
from app.schemas.typings.mfa.constrained_integers import MfaAttemptCount, TotpTimeStep
from app.schemas.typings.mfa.prefixed_id import MfaChallengeId, RecoveryCodeId
from app.schemas.typings.mfa.strings import SealedTotpSecret
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.users.prefixed_id import UserId


class TotpFactorRepoContract(RepoContract, Protocol):
    """A user's authenticator, stored under the user's id (one per user)."""

    def get_for_user(self, user_id: UserId) -> TotpFactorDocument | None:
        raise NotImplementedError

    def start_enrollment(self, factor: TotpFactorDocument) -> bool:
        """
        Store a new PENDING factor in one atomic step, replacing a pending
        one of the same user. False, and nothing written, when the user's
        factor is ACTIVE (it must be removed first).
        """
        raise NotImplementedError

    def activate(
        self, user_id: UserId, step: TotpTimeStep, now: Microseconds
    ) -> TotpFactorDocument | None:
        """
        Turn the user's PENDING factor ACTIVE with its first accepted code's
        step, in one atomic step; None when it is not pending any more.
        """
        raise NotImplementedError

    def record_use(
        self, user_id: UserId, step: TotpTimeStep, now: Microseconds
    ) -> TotpFactorDocument | None:
        """
        Remember an accepted code of the ACTIVE factor (compare-and-swap):
        only a step later than the last used one is recorded. None, and
        nothing written, when the step was already used (a replayed or a
        parallel code) or the factor is not active.
        """
        raise NotImplementedError

    def replace_sealed_secret(
        self,
        user_id: UserId,
        expected: SealedTotpSecret,
        resealed: SealedTotpSecret,
        now: Microseconds,
    ) -> bool:
        """
        Store the same secret sealed with another key, in one atomic step,
        only while the stored one is still `expected` (the key rotation
        job); False when the factor changed or is gone.
        """
        raise NotImplementedError

    def delete_for_user(self, user_id: UserId) -> None:
        raise NotImplementedError

    def list_after(self, after: TotpFactorDocument | None) -> list[TotpFactorDocument]:
        """
        The next batch of factors in the order they were created, after
        `after` (from the first when None); an empty list after the last.
        The key rotation job walks them to re-seal their secrets (a keyset
        page on the indexed `created_at`, never the whole table at once).
        """
        raise NotImplementedError


class RecoveryCodeRepoContract(RepoContract, Protocol):
    def list_for_user(self, user_id: UserId) -> list[RecoveryCodeDocument]:
        """A user's codes, used ones included (indexed by user)."""
        raise NotImplementedError

    def replace_for_user(
        self, user_id: UserId, codes: Sequence[RecoveryCodeDocument]
    ) -> None:
        """Drop the user's codes and store a new set."""
        raise NotImplementedError

    def spend(
        self, code_id: RecoveryCodeId, now: Microseconds
    ) -> RecoveryCodeDocument | None:
        """
        Mark a code used in one atomic step (compare-and-swap on `used_at`):
        the spent code, or None when it was already used or is missing.
        """
        raise NotImplementedError

    def delete_for_user(self, user_id: UserId) -> None:
        raise NotImplementedError


class MfaChallengeRepoContract(RepoContract, Protocol):
    def save(self, challenge: MfaChallengeDocument) -> None:
        raise NotImplementedError

    def get(self, challenge_id: MfaChallengeId) -> MfaChallengeDocument | None:
        raise NotImplementedError

    def register_failed_attempt(
        self,
        challenge_id: MfaChallengeId,
        max_failed_attempts: MfaAttemptCount,
        now: Microseconds,
    ) -> MfaAttemptCount | None:
        """
        Count one more code check in one atomic step while the challenge is
        open (not consumed, below the limit): the new count, or None when
        nothing was counted. Parallel callers each get a different count.
        """
        raise NotImplementedError

    def consume(
        self, challenge_id: MfaChallengeId, now: Microseconds
    ) -> MfaChallengeDocument | None:
        """
        Mark the challenge consumed (compare-and-swap): the consumed
        challenge, or None when another request consumed it first.
        """
        raise NotImplementedError

    def delete_created_before(self, created_before: Microseconds) -> DocumentCount:
        """Purge challenges created before a moment; returns how many."""
        raise NotImplementedError
