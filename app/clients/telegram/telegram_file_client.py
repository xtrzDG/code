from typing import NoReturn

import httpx

from app.clients.http.media_download import download_capped
from app.clients.telegram.telegram_bot_client import TELEGRAM_API_BASE_URL
from app.contracts.channel_clients import ProviderToken
from app.contracts.media_clients import TelegramFileClientContract
from app.schemas.dto.media import FetchedMedia, TelegramFileInfo
from app.schemas.exceptions.application_errors import (
    ChannelCredentialRejectedError,
    ExternalServiceError,
)
from app.schemas.exceptions.media_errors import MediaUnavailableError
from app.schemas.typings.media.constrained_integers import MediaByteCount
from app.schemas.typings.media.strings import (
    ProviderMediaId,
    ProviderMediaType,
    TelegramFilePath,
)
from app.utilities.channels.json_values import (
    JsonObject,
    as_object,
    parse_json_object,
    read_integer,
    read_text,
)

LOOKUP_TIMEOUT_SECONDS: float = 10.0
DOWNLOAD_TIMEOUT_SECONDS: float = 30.0
REJECTED_TOKEN_ERROR_CODES: frozenset[int] = frozenset({401, 404})
CLIENT_ERROR_CODES: range = range(400, 500)


class TelegramFileClient(TelegramFileClientContract):
    """
    Files of the Bot API: `getFile` names where a file lies, then
    `/file/bot<token>/<file_path>` serves it (files of at most 20 MB). The
    bot token is part of both paths, so it never appears in errors and
    transport errors are not chained into them.
    """

    def __init__(
        self,
        transport: httpx.BaseTransport | None = None,
        base_url: str = TELEGRAM_API_BASE_URL,
    ) -> None:
        self._base_url: str = base_url.rstrip("/")
        self._http_client: httpx.Client = httpx.Client(
            base_url=self._base_url,
            timeout=LOOKUP_TIMEOUT_SECONDS,
            transport=transport,
        )
        self._download_client: httpx.Client = httpx.Client(
            base_url=self._base_url,
            timeout=DOWNLOAD_TIMEOUT_SECONDS,
            transport=transport,
            follow_redirects=False,
        )

    def get_file(
        self, bot_token: ProviderToken, file_id: ProviderMediaId
    ) -> TelegramFileInfo:
        try:
            response: httpx.Response = self._http_client.post(
                f"/bot{bot_token}/getFile", json={"file_id": str(file_id)}
            )
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                f"Telegram getFile failed: {type(error).__name__}."
            ) from None

        body: JsonObject = parse_json_object(response.content) or {}
        result: JsonObject | None = (
            as_object(body.get("result")) if body.get("ok") is True else None
        )
        if result is None:
            raise_get_file_error(body, response.status_code)

        file_path: str | None = read_text(result, "file_path")
        if file_path is None:
            raise MediaUnavailableError("Telegram no longer serves this file.")

        size: int | None = read_integer(result, "file_size")
        return TelegramFileInfo(
            file_path=TelegramFilePath(file_path),
            file_size=None if size is None or size < 0 else MediaByteCount(size),
        )

    def download_file(
        self, bot_token: ProviderToken, file_path: TelegramFilePath, max_bytes: int
    ) -> FetchedMedia:
        content, content_type = download_capped(
            self._download_client,
            f"/file/bot{bot_token}/{file_path}",
            {},
            max_bytes,
            "Telegram",
        )
        return FetchedMedia(
            content=content,
            declared_type=(
                None if content_type is None else ProviderMediaType(content_type)
            ),
        )


def raise_get_file_error(body: JsonObject, status_code: int) -> NoReturn:
    error_code: int = read_integer(body, "error_code") or status_code
    description: str = read_text(body, "description") or "unknown error"
    if error_code in REJECTED_TOKEN_ERROR_CODES:
        raise ChannelCredentialRejectedError(
            f"Telegram getFile rejected the bot token ({error_code})."
        )

    if error_code in CLIENT_ERROR_CODES:
        raise MediaUnavailableError(
            f"Telegram getFile refused the file ({error_code}): {description}"
        )

    raise ExternalServiceError(f"Telegram getFile failed ({error_code}): {description}")
