import httpx

from app.clients.http.media_download import download_capped
from app.clients.meta.meta_graph_client import (
    DEFAULT_GRAPH_API_VERSION,
    META_GRAPH_BASE_URL,
)
from app.clients.meta.meta_graph_errors import build_graph_error
from app.contracts.channel_clients import ProviderToken
from app.contracts.media_clients import MetaMediaClientContract
from app.schemas.dto.media import FetchedMedia, WhatsAppMediaInfo
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ProviderRejectedMessageError,
)
from app.schemas.exceptions.media_errors import MediaUnavailableError
from app.schemas.typings.media.constrained_integers import MediaByteCount
from app.schemas.typings.media.strings import (
    MediaDownloadUrl,
    ProviderMediaId,
    ProviderMediaType,
)
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_integer,
    read_text,
)

# A download is larger than an API call: a voice note of several megabytes
# on a slow link still arrives.
DOWNLOAD_TIMEOUT_SECONDS: float = 30.0
LOOKUP_TIMEOUT_SECONDS: float = 10.0


class MetaMediaClient(MetaMediaClientContract):
    """
    Media of the WhatsApp Cloud API (`GET /{media-id}` gives a short-lived
    URL that needs the token) and attachment files of Messenger and
    Instagram (a CDN URL in the webhook). Tokens travel in the
    Authorization header; errors never name the URL.
    """

    def __init__(
        self,
        transport: httpx.BaseTransport | None = None,
        api_version: str = DEFAULT_GRAPH_API_VERSION,
        base_url: str = META_GRAPH_BASE_URL,
    ) -> None:
        self._graph_client: httpx.Client = httpx.Client(
            base_url=f"{base_url.rstrip('/')}/{api_version}",
            timeout=LOOKUP_TIMEOUT_SECONDS,
            transport=transport,
        )
        self._download_client: httpx.Client = httpx.Client(
            timeout=DOWNLOAD_TIMEOUT_SECONDS,
            transport=transport,
            follow_redirects=False,
        )

    def read_whatsapp_media(
        self, access_token: ProviderToken, media_id: ProviderMediaId
    ) -> WhatsAppMediaInfo:
        try:
            response: httpx.Response = self._graph_client.get(
                f"/{media_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                f"Meta media lookup failed: {type(error).__name__}."
            ) from None

        body: JsonObject = parse_json_object(response.content) or {}
        if response.status_code >= 400 or "error" in body:
            graph_error = build_graph_error(
                response.status_code, body, None, is_lookup=False
            )
            if isinstance(graph_error, ProviderRejectedMessageError):
                raise MediaUnavailableError(str(graph_error)) from None

            raise graph_error

        url: str | None = read_text(body, "url")
        if url is None:
            raise MediaUnavailableError("Meta returned no URL for the media file.")

        size: int | None = read_integer(body, "file_size")
        mime_type: str | None = read_text(body, "mime_type")
        return WhatsAppMediaInfo(
            url=MediaDownloadUrl(url),
            mime_type=None if mime_type is None else ProviderMediaType(mime_type),
            file_size=None if size is None or size < 0 else MediaByteCount(size),
        )

    def download(
        self,
        url: MediaDownloadUrl,
        access_token: ProviderToken | None,
        max_bytes: int,
    ) -> FetchedMedia:
        headers: dict[str, str] = (
            {} if access_token is None else {"Authorization": f"Bearer {access_token}"}
        )
        content, content_type = download_capped(
            self._download_client, str(url), headers, max_bytes, "Meta"
        )
        return FetchedMedia(
            content=content,
            declared_type=(
                None if content_type is None else ProviderMediaType(content_type)
            ),
        )
