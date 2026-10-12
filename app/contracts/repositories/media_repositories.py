"""Persistence of the files customers sent and uploaded, read only per business."""

from collections.abc import Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.message_media import MessageMediaDocument
from app.schemas.domain.widget_uploads import WidgetUploadDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import WidgetVisitorId
from app.schemas.typings.media.prefixed_id import MessageMediaId, WidgetUploadId


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


class WidgetUploadRepoContract(RepoContract, Protocol):
    """Files website chat visitors uploaded, read only per business."""

    def save(self, upload: WidgetUploadDocument) -> None:
        raise NotImplementedError

    def get_many(
        self, business_id: BusinessId, upload_ids: Sequence[WidgetUploadId]
    ) -> list[WidgetUploadDocument]:
        """The business's uploads of these ids, in one read (others skipped)."""
        raise NotImplementedError

    def claim(
        self,
        business_id: BusinessId,
        upload_id: WidgetUploadId,
        visitor_id: WidgetVisitorId,
        at: Microseconds,
    ) -> WidgetUploadDocument | None:
        """
        Mark the upload attached to a message of its own visitor, in one
        step (a row lock on Postgres): None, and nothing written, when it is
        missing, another visitor's or attached already.
        """
        raise NotImplementedError

    def release(self, business_id: BusinessId, upload_id: WidgetUploadId) -> None:
        """
        Give a claimed upload back (its message was not queued after all):
        not attached any more; nothing happens to a missing one.
        """
        raise NotImplementedError

    def list_created_before(
        self, business_id: BusinessId, created_before: Microseconds
    ) -> list[WidgetUploadDocument]:
        """The business's uploads that came before a moment, oldest first."""
        raise NotImplementedError

    def delete(self, business_id: BusinessId, upload_id: WidgetUploadId) -> None:
        raise NotImplementedError
