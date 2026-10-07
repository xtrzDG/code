"""Persistence of the stored files customers sent, read only per business."""

from collections.abc import Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.message_media import MessageMediaDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.media.prefixed_id import MessageMediaId


class MessageMediaRepoContract(RepoContract, Protocol):
    def save(self, media: MessageMediaDocument) -> None:
        raise NotImplementedError

    def get(
        self, business_id: BusinessId, media_id: MessageMediaId
    ) -> MessageMediaDocument | None:
        raise NotImplementedError

    def get_many(
        self, business_id: BusinessId, media_ids: Sequence[MessageMediaId]
    ) -> list[MessageMediaDocument]:
        """The business's files of these ids, in one read (others skipped)."""
        raise NotImplementedError

    def list_created_before(
        self, business_id: BusinessId, created_before: Microseconds
    ) -> list[MessageMediaDocument]:
        """The business's files stored before a moment, oldest first."""
        raise NotImplementedError

    def delete(self, business_id: BusinessId, media_id: MessageMediaId) -> None:
        raise NotImplementedError
