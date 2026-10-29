"""Mock transports and requests for the media download tests."""

from collections.abc import Callable

import httpx

from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.media import ChannelMediaRequest
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.media.constrained_integers import MediaByteLimit
from app.schemas.typings.media.strings import ProviderMediaId

BOT_TOKEN: str = "123456:test-token-0000"
CDN_URL: str = "https://lookaside.fbsbx.com/whatsapp_business/attachments/?mid=1"
LIMIT: MediaByteLimit = MediaByteLimit(64 * 1024)

type Handler = Callable[[httpx.Request], httpx.Response]


def recording(handler: Handler) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    return httpx.MockTransport(answer), seen


def request_for(
    channel: ChannelKind, media_id: str, credential: str | None = None
) -> ChannelMediaRequest:
    return ChannelMediaRequest(
        channel=channel,
        provider_media_id=ProviderMediaId(media_id),
        credential=None if credential is None else ChannelSecret(credential),
        max_bytes=LIMIT,
    )
