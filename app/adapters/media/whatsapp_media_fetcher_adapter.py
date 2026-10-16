from app.contracts.channel_media import ChannelMediaFetcherContract
from app.contracts.media_clients import MetaMediaClientContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.media import ChannelMediaRequest, FetchedMedia, WhatsAppMediaInfo
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.media_errors import MediaTooLargeError
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.media.media_hosts import require_meta_media_url


class WhatsAppMediaFetcherAdapter(ChannelMediaFetcherContract):
    """
    A WhatsApp Cloud API media file: look its id up (`GET /{media-id}`,
    the platform's system user token) for a URL valid a few minutes, then
    download it with the same token. A declared size over the cap is
    refused before anything is downloaded.
    """

    def __init__(
        self, meta_media_client: MetaMediaClientContract, app_settings: AppSettings
    ) -> None:
        self._meta_media_client: MetaMediaClientContract = meta_media_client
        self._app_settings: AppSettings = app_settings

    def fetch(self, request: ChannelMediaRequest) -> FetchedMedia:
        access_token: PlatformSecret | None = (
            self._app_settings.whatsapp_system_user_token
        )
        if access_token is None:
            raise ExternalServiceError(
                "WhatsApp is not configured: WHATSAPP_SYSTEM_USER_TOKEN is missing."
            )

        info: WhatsAppMediaInfo = self._meta_media_client.read_whatsapp_media(
            access_token, request.provider_media_id
        )
        if info.file_size is not None and int(info.file_size) > int(request.max_bytes):
            raise MediaTooLargeError("The WhatsApp file is larger than allowed.")

        fetched: FetchedMedia = self._meta_media_client.download(
            require_meta_media_url(str(info.url)),
            access_token,
            int(request.max_bytes),
        )
        return fetched.model_copy(
            update={"declared_type": info.mime_type or fetched.declared_type}
        )
