"""
Persistence contracts of users, their one-time login codes and sessions.

Implementations return independent copies: mutating a returned document does
not change stored state until it is saved.
"""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.users import (
    OtpChallengeDocument,
    UserDocument,
    UserSessionDocument,
)
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
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

    def delete(self, challenge_id: OtpChallengeId) -> None:
        """Drop a challenge whose code could not be delivered."""
        raise NotImplementedError


class UserSessionRepoContract(RepoContract, Protocol):
    def save(self, session: UserSessionDocument) -> None:
        raise NotImplementedError

    def find_by_token_hash(
        self,
        token_hash: AccessTokenHash,
    ) -> UserSessionDocument | None:
        raise NotImplementedError

    def delete(self, session_id: UserSessionId) -> None:
        raise NotImplementedError
