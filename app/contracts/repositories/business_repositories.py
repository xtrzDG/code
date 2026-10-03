"""
Persistence contracts of businesses, their channels and profiles.

Implementations return independent copies: mutating a returned document does
not change stored state until it is saved. Every business-owned document is
looked up through its business id, so one tenant never sees another's data.
"""

from collections.abc import Callable
from typing import Protocol

from app.contracts.repo_contract import RepoContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.users.prefixed_id import UserId


class BusinessRepoContract(RepoContract, Protocol):
    def save(self, business: BusinessDocument) -> None:
        """
        Store the whole business and raise its `revision` (on the given
        document too) above the stored one, in one step with the write. For
        creating a business; a change of an existing one goes through
        `update` (or `save_if_unchanged`), which cannot overwrite what
        others saved since this copy was read.
        """
        raise NotImplementedError

    def update(
        self,
        business_id: BusinessId,
        apply: Callable[[BusinessDocument], None],
    ) -> BusinessDocument:
        """
        Apply a change to the business as stored now and store it, raising
        the revision by one, in one step (no other save can come in
        between). `apply` changes only the fields its writer owns and may
        raise to refuse (nothing is stored then); a change that leaves the
        document as it was stores nothing. Returns the business as stored;
        NotFoundError when it does not exist.
        """
        raise NotImplementedError

    def save_if_unchanged(self, business: BusinessDocument) -> bool:
        """
        Store the business only while the stored revision is still the one
        this document carries (nobody saved since it was read), raising the
        revision by one. False, and nothing stored, otherwise.
        """
        raise NotImplementedError

    def get(self, business_id: BusinessId) -> BusinessDocument | None:
        raise NotImplementedError

    def list_by_member(self, user_id: UserId) -> list[BusinessDocument]:
        """Businesses where the user is an owner or staff member."""
        raise NotImplementedError

    def list_all(self) -> list[BusinessDocument]:
        """Every business (platform admin views and background jobs only)."""
        raise NotImplementedError


class ChannelRepoContract(RepoContract, Protocol):
    def save(self, channel: ChannelDocument) -> None:
        raise NotImplementedError

    def get(self, channel_id: ChannelId) -> ChannelDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[ChannelDocument]:
        raise NotImplementedError

    def find_by_external_id(
        self,
        kind: ChannelKind,
        external_id: ChannelExternalId,
    ) -> ChannelDocument | None:
        """Resolve the tenant of an incoming webhook from the channel account."""
        raise NotImplementedError


class BusinessProfileRepoContract(RepoContract, Protocol):
    def save(self, profile: BusinessProfileDocument) -> None:
        raise NotImplementedError

    def get_by_business(
        self,
        business_id: BusinessId,
    ) -> BusinessProfileDocument | None:
        raise NotImplementedError

    def insert_if_absent(self, profile: BusinessProfileDocument) -> bool:
        """Store a first profile unless the business has one (atomic)."""
        raise NotImplementedError

    def modify(
        self,
        business_id: BusinessId,
        change: Callable[[BusinessProfileDocument], BusinessProfileDocument | None],
    ) -> BusinessProfileDocument | None:
        """
        Store what `change` makes of the profile as stored now, in one step
        (no other save comes in between); None, and nothing written, when
        there is no profile or `change` returns None.
        """
        raise NotImplementedError
