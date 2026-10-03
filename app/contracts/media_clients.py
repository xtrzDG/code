"""Thin clients of the messaging platforms' file downloads."""

from typing import Protocol

from app.contracts.channel_clients import ProviderToken
from app.contracts.client_contract import ClientContract
from app.schemas.dto.media import FetchedMedia, TelegramFileInfo, WhatsAppMediaInfo
from app.schemas.typings.media.strings import (
    MediaDownloadUrl,
    ProviderMediaId,
    TelegramFilePath,
)


class MetaMediaClientContract(ClientContract, Protocol):
    def read_whatsapp_media(
        self, access_token: ProviderToken, media_id: ProviderMediaId
    ) -> WhatsAppMediaInfo:
        """
        GET /{media-id}: the file's current download URL, type and size.
        Raises MediaUnavailableError for a media id the Cloud API no longer
        knows, ChannelCredentialRejectedError for a token it refuses,
        ExternalServiceError otherwise.
        """
        raise NotImplementedError

    def download(
        self,
        url: MediaDownloadUrl,
        access_token: ProviderToken | None,
        max_bytes: int,
    ) -> FetchedMedia:
        """
        The file at a Meta address (sent with the token when given); raises
        MediaTooLargeError, MediaUnavailableError or ExternalServiceError.
        """
        raise NotImplementedError


class TelegramFileClientContract(ClientContract, Protocol):
    def get_file(
        self, bot_token: ProviderToken, file_id: ProviderMediaId
    ) -> TelegramFileInfo:
        """getFile: where Telegram serves the file; raises MediaUnavailableError."""
        raise NotImplementedError

    def download_file(
        self, bot_token: ProviderToken, file_path: TelegramFilePath, max_bytes: int
    ) -> FetchedMedia:
        """
        The file's bytes; raises MediaTooLargeError, MediaUnavailableError or
        ExternalServiceError (never with the token in the message).
        """
        raise NotImplementedError
