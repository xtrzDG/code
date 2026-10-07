"""Persistence contracts of the sub-processor change notices (migration 1124)."""

from typing import Protocol

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.legal import (
    SubprocessorAnnouncementDocument,
    SubprocessorNoticeDocument,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.legal.constrained_strings import SubprocessorChangeKey


class SubprocessorNoticeRepoContract(RepoContract, Protocol):
    def find(
        self, business_id: BusinessId, change_key: SubprocessorChangeKey
    ) -> SubprocessorNoticeDocument | None:
        """The notice the business got about this change, if any."""
        raise NotImplementedError

    def record_once(self, notice: SubprocessorNoticeDocument) -> bool:
        """
        Store a notice unless the business already has one for the change
        (atomic, also across processes); True when it was stored now.
        """
        raise NotImplementedError


class SubprocessorAnnouncementRepoContract(RepoContract, Protocol):
    def get(
        self, change_key: SubprocessorChangeKey
    ) -> SubprocessorAnnouncementDocument | None:
        """The announcement of a change, once its notice period opened."""
        raise NotImplementedError

    def save(self, announcement: SubprocessorAnnouncementDocument) -> None:
        raise NotImplementedError
