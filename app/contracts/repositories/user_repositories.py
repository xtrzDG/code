"""
Persistence contracts of users, their one-time login codes and sessions.

Implementations return independent copies: mutating a returned document does
not change stored state until it is saved.
"""

from collections.abc import Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.constants.mfa import AuthLevel
from app.schemas.domain.users import (
    OtpChallengeDocument,
    UserDocument,
    UserSessionDocument,
)
from app.schemas.dto.sessions import SessionActivity
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.users.constrained_integers import OtpAttemptCount
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import OtpChallengeId, UserId, UserSessionId
from app.schemas.typings.users.strings import AccessTokenHash


class UserRepoContract(RepoContract, Protocol):
    def save(self, user: UserDocument) -> None:
        raise NotImplementedError

    def get(self, user_id: UserId) -> UserDocument | None:
        raise NotImplementedError

    def find_by_phone_number(
        self,
        phone_number: E164PhoneNumber,
    ) -> UserDocument | None:
        raise NotImplementedError

    def find_by_email(self, email: EmailAddress) -> UserDocument | None:
        raise NotImplementedError

    def get_many(self, user_ids: Sequence[UserId]) -> list[UserDocument]:
        """The stored users of these ids (missing ones skipped), one read."""
        raise NotImplementedError

    def list_created_between(
        self, created_from: Microseconds, created_before: Microseconds
    ) -> list[UserDocument]:
        """Accounts created in [from, before), oldest first (indexed)."""
        raise NotImplementedError


class OtpChallengeRepoContract(RepoContract, Protocol):
    def save(self, challenge: OtpChallengeDocument) -> None:
        raise NotImplementedError

    def get(self, challenge_id: OtpChallengeId) -> OtpChallengeDocument | None:
        raise NotImplementedError

    def list_created_since(
        self,
        created_after: Microseconds,
    ) -> list[OtpChallengeDocument]:
        """Challenges created after a moment (throttling of repeated logins)."""
        raise NotImplementedError

    def register_failed_attempt(
        self,
        challenge_id: OtpChallengeId,
        max_failed_attempts: OtpAttemptCount,
        now: Microseconds,
    ) -> OtpAttemptCount | None:
        """
        Count one more failed code check in one atomic step (a row lock on
        Postgres, the collection lock in memory), only while the challenge
        is open: not consumed and below `max_failed_attempts`. Returns the
        new count, or None when nothing was counted (missing, consumed or
        locked). Parallel callers each get a different count, so at most
        `max_failed_attempts` of them get one.
        """
        raise NotImplementedError

    def consume(
        self,
        challenge_id: OtpChallengeId,
        now: Microseconds,
    ) -> OtpChallengeDocument | None:
        """
        Mark the challenge consumed in one atomic step (compare-and-swap on
        `is_consumed`): the consumed challenge, or None when it is missing
        or another request consumed it first.
        """
        raise NotImplementedError

    def delete(self, challenge_id: OtpChallengeId) -> None:
        """Drop a challenge whose code could not be delivered."""
        raise NotImplementedError

    def delete_created_before(self, created_before: Microseconds) -> DocumentCount:
        """Purge challenges created before a moment; returns how many."""
        raise NotImplementedError


class UserSessionRepoContract(RepoContract, Protocol):
    def save(self, session: UserSessionDocument) -> None:
        raise NotImplementedError

    def get(self, session_id: UserSessionId) -> UserSessionDocument | None:
        raise NotImplementedError

    def record_authentication(
        self,
        session_id: UserSessionId,
        auth_level: AuthLevel,
        authenticated_at: Microseconds,
    ) -> UserSessionDocument | None:
        """
        Set how the session is signed in and when its person last proved it
        is them (a passed step-up, a confirmed or removed authenticator), in
        one atomic step; None when the session is gone.
        """
        raise NotImplementedError

    def record_activity(
        self,
        session_id: UserSessionId,
        activity: SessionActivity,
    ) -> UserSessionDocument | None:
        """
        Record a use of the session in one atomic step: when and from
        where it was last seen, the browser it names (when it sent one),
        the new idle expiry and the (possibly earlier) absolute expiry;
        None when the session is gone.
        """
        raise NotImplementedError

    def find_by_token_hash(
        self,
        token_hash: AccessTokenHash,
    ) -> UserSessionDocument | None:
        raise NotImplementedError

    def list_by_user(self, user_id: UserId) -> list[UserSessionDocument]:
        """Every stored session of a person (indexed; a short list)."""
        raise NotImplementedError

    def set_level_for_user(
        self,
        user_id: UserId,
        auth_level: AuthLevel,
        now: Microseconds,
        except_session_id: UserSessionId | None = None,
    ) -> DocumentCount:
        """
        Make every session of the person (but `except_session_id`) count as
        signed in with `auth_level`, each in one atomic step; when they last
        proved it is them stays. Returns how many sessions changed level.
        """
        raise NotImplementedError

    def delete_for_user(
        self,
        user_id: UserId,
        except_session_id: UserSessionId | None = None,
    ) -> DocumentCount:
        """
        End every session of the person but `except_session_id` (their
        tokens stop working with the next request); returns how many ended.
        """
        raise NotImplementedError

    def delete(self, session_id: UserSessionId) -> None:
        raise NotImplementedError

    def delete_expired(self, now: Microseconds) -> DocumentCount:
        """
        Purge sessions whose absolute expiry has come (expires_at <= now)
        and those unused too long (idle_expires_at <= now).
        """
        raise NotImplementedError
