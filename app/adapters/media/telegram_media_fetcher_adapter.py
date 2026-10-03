from app.contracts.channel_media import ChannelMediaFetcherContract
from app.contracts.media_clients import TelegramFileClientContract
from app.schemas.dto.media import ChannelMediaRequest, FetchedMedia, TelegramFileInfo
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.media_errors import MediaTooLargeError


class TelegramMediaFetcherAdapter(ChannelMediaFetcherContract):
    """
    A file of a Telegram message: `getFile` with the business's bot token
    names where it lies (and its size, refused over the cap before the
    download), then the file is downloaded.
    """

    def __init__(self, telegram_file_client: TelegramFileClientContract) -> None:
        self._telegram_file_client: TelegramFileClientContract = telegram_file_client

    def fetch(self, request: ChannelMediaRequest) -> FetchedMedia:
        if request.credential is None:
            raise ExternalServiceError(
                "The Telegram bot of this business is not connected."
            )

        info: TelegramFileInfo = self._telegram_file_client.get_file(
            request.credential, request.provider_media_id
        )
        if info.file_size is not None and int(info.file_size) > int(request.max_bytes):
            raise MediaTooLargeError("The Telegram file is larger than allowed.")

        return self._telegram_file_client.download_file(
            request.credential, info.file_path, int(request.max_bytes)
        )
