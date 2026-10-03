"""
Downloading customer files from the platforms: WhatsApp's Graph lookup and
download, Telegram's getFile, Messenger and Instagram CDN addresses; size
caps before and while downloading, and errors that never carry a token.
"""

from collections.abc import Callable

import httpx
import pytest

from app.adapters.media.meta_page_media_fetcher_adapter import (
    MetaPageMediaFetcherAdapter,
)
from app.adapters.media.routing_channel_media_fetcher_adapter import (
    RoutingChannelMediaFetcherAdapter,
)
from app.adapters.media.telegram_media_fetcher_adapter import (
    TelegramMediaFetcherAdapter,
)
from app.adapters.media.whatsapp_media_fetcher_adapter import (
    WhatsAppMediaFetcherAdapter,
)
from app.clients.meta.meta_media_client import MetaMediaClient
from app.clients.telegram.telegram_file_client import TelegramFileClient
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.media import ChannelMediaRequest
from app.schemas.exceptions.application_errors import (
    ChannelCredentialRejectedError,
    ExternalServiceError,
)
from app.schemas.exceptions.media_errors import (
    MediaTooLargeError,
    MediaUnavailableError,
)
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.media.constrained_integers import MediaByteLimit
from app.schemas.typings.media.strings import ProviderMediaId
from tests.channels.channels_settings import WHATSAPP_SYSTEM_TOKEN, build_settings
from tests.media.media_fakes import jpeg_bytes, ogg_opus_bytes

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


class TestWhatsApp:
    def fetcher(self, handler: Handler) -> tuple[WhatsAppMediaFetcherAdapter, list]:
        transport, seen = recording(handler)
        return (
            WhatsAppMediaFetcherAdapter(
                MetaMediaClient(transport=transport), build_settings()
            ),
            seen,
        )

    def test_looks_the_id_up_then_downloads_with_the_system_token(self) -> None:
        audio = ogg_opus_bytes()

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.host == "graph.facebook.com":
                return httpx.Response(
                    200,
                    json={
                        "url": CDN_URL,
                        "mime_type": "audio/ogg; codecs=opus",
                        "file_size": len(audio),
                        "id": "1003383421387256",
                        "messaging_product": "whatsapp",
                    },
                )
            return httpx.Response(
                200, content=audio, headers={"Content-Type": "application/octet-stream"}
            )

        fetcher, seen = self.fetcher(handler)
        fetched = fetcher.fetch(request_for(ChannelKind.WHATSAPP, "1003383421387256"))

        assert fetched.content == audio
        # The type the lookup declared wins over the CDN's generic one.
        assert fetched.declared_type == "audio/ogg; codecs=opus"
        assert [request.url.path.rsplit("/", 1)[-1] for request in seen][:1] == [
            "1003383421387256"
        ]
        assert all(
            request.headers["Authorization"] == f"Bearer {WHATSAPP_SYSTEM_TOKEN}"
            for request in seen
        )

    def test_a_declared_size_over_the_cap_is_refused_before_downloading(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"url": CDN_URL, "file_size": int(LIMIT) + 1}
            )

        fetcher, seen = self.fetcher(handler)
        with pytest.raises(MediaTooLargeError):
            fetcher.fetch(request_for(ChannelKind.WHATSAPP, "1"))
        assert len(seen) == 1

    def test_an_address_off_meta_hosts_is_never_fetched(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"url": "https://attacker.example/x"})

        fetcher, seen = self.fetcher(handler)
        with pytest.raises(MediaUnavailableError):
            fetcher.fetch(request_for(ChannelKind.WHATSAPP, "1"))
        assert len(seen) == 1

    def test_an_expired_id_is_unavailable_and_an_outage_is_temporary(self) -> None:
        def expired(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                400,
                json={"error": {"message": "Invalid media id", "code": 100}},
            )

        fetcher, _ = self.fetcher(expired)
        with pytest.raises(ExternalServiceError):
            fetcher.fetch(request_for(ChannelKind.WHATSAPP, "1"))

        def outage(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("down")

        fetcher, _ = self.fetcher(outage)
        with pytest.raises(ExternalServiceError) as raised:
            fetcher.fetch(request_for(ChannelKind.WHATSAPP, "1"))
        assert not isinstance(raised.value, MediaUnavailableError)

    def test_no_system_token_means_whatsapp_is_not_configured(self) -> None:
        transport, _ = recording(lambda request: httpx.Response(200))
        fetcher = WhatsAppMediaFetcherAdapter(
            MetaMediaClient(transport=transport),
            build_settings(WHATSAPP_SYSTEM_USER_TOKEN=""),
        )
        with pytest.raises(ExternalServiceError, match="WHATSAPP_SYSTEM_USER_TOKEN"):
            fetcher.fetch(request_for(ChannelKind.WHATSAPP, "1"))

    def test_a_lookup_without_an_address_is_unavailable(self) -> None:
        fetcher, _ = self.fetcher(lambda request: httpx.Response(200, json={}))
        with pytest.raises(MediaUnavailableError):
            fetcher.fetch(request_for(ChannelKind.WHATSAPP, "1"))


class TestTelegram:
    def fetcher(self, handler: Handler) -> tuple[TelegramMediaFetcherAdapter, list]:
        transport, seen = recording(handler)
        return TelegramMediaFetcherAdapter(TelegramFileClient(transport=transport)), seen

    def test_get_file_then_the_file_with_the_business_bot_token(self) -> None:
        photo = jpeg_bytes()

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/getFile"):
                return httpx.Response(
                    200,
                    json={
                        "ok": True,
                        "result": {
                            "file_id": "photo-file-large",
                            "file_size": len(photo),
                            "file_path": "photos/file_7.jpg",
                        },
                    },
                )
            return httpx.Response(200, content=photo)

        fetcher, seen = self.fetcher(handler)
        fetched = fetcher.fetch(
            request_for(ChannelKind.TELEGRAM, "photo-file-large", BOT_TOKEN)
        )

        assert fetched.content == photo
        assert [request.url.path for request in seen] == [
            f"/bot{BOT_TOKEN}/getFile",
            f"/file/bot{BOT_TOKEN}/photos/file_7.jpg",
        ]

    def test_size_caps_before_and_while_downloading(self) -> None:
        def declared_too_big(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"ok": True, "result": {"file_path": "a", "file_size": 10**8}},
            )

        fetcher, seen = self.fetcher(declared_too_big)
        with pytest.raises(MediaTooLargeError):
            fetcher.fetch(request_for(ChannelKind.TELEGRAM, "f", BOT_TOKEN))
        assert len(seen) == 1

        def body_too_big(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/getFile"):
                return httpx.Response(
                    200, json={"ok": True, "result": {"file_path": "voice/a.oga"}}
                )
            return httpx.Response(200, content=b"x" * (int(LIMIT) + 10))

        fetcher, _ = self.fetcher(body_too_big)
        with pytest.raises(MediaTooLargeError):
            fetcher.fetch(request_for(ChannelKind.TELEGRAM, "f", BOT_TOKEN))

    @pytest.mark.parametrize(
        ("status", "body", "error"),
        [
            (401, {"ok": False, "error_code": 401, "description": "Unauthorized"},
             ChannelCredentialRejectedError),
            (400, {"ok": False, "error_code": 400, "description": "file is too big"},
             MediaUnavailableError),
            (502, {"ok": False, "error_code": 502, "description": "Bad Gateway"},
             ExternalServiceError),
            (200, {"ok": True, "result": {"file_id": "f"}}, MediaUnavailableError),
        ],
    )
    def test_get_file_errors(
        self, status: int, body: dict[str, object], error: type[Exception]
    ) -> None:
        fetcher, _ = self.fetcher(lambda request: httpx.Response(status, json=body))
        with pytest.raises(error) as raised:
            fetcher.fetch(request_for(ChannelKind.TELEGRAM, "f", BOT_TOKEN))
        assert BOT_TOKEN not in str(raised.value)

    def test_transport_errors_never_carry_the_token(self) -> None:
        def broken(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout(f"timed out reading {request.url}")

        fetcher, _ = self.fetcher(broken)
        with pytest.raises(ExternalServiceError) as raised:
            fetcher.fetch(request_for(ChannelKind.TELEGRAM, "f", BOT_TOKEN))
        assert BOT_TOKEN not in str(raised.value)
        assert raised.value.__cause__ is None

    def test_a_business_without_its_bot_cannot_fetch(self) -> None:
        fetcher, seen = self.fetcher(lambda request: httpx.Response(200))
        with pytest.raises(ExternalServiceError):
            fetcher.fetch(request_for(ChannelKind.TELEGRAM, "f"))
        assert seen == []


class TestMetaPages:
    def test_a_cdn_address_is_downloaded_without_a_token(self) -> None:
        audio = ogg_opus_bytes()
        transport, seen = recording(
            lambda request: httpx.Response(
                200, content=audio, headers={"Content-Type": "audio/mp4"}
            )
        )
        fetcher = MetaPageMediaFetcherAdapter(MetaMediaClient(transport=transport))

        fetched = fetcher.fetch(
            request_for(
                ChannelKind.INSTAGRAM,
                "https://lookaside.fbsbx.com/ig_messaging_cdn/?asset_id=1801",
            )
        )

        assert fetched.content == audio
        assert fetched.declared_type == "audio/mp4"
        assert "Authorization" not in seen[0].headers

    @pytest.mark.parametrize(
        "address",
        [
            "http://cdn.fbsbx.com/v/voice.mp4",
            "https://cdn.fbsbx.com.attacker.example/voice.mp4",
            "https://user:pass@cdn.fbsbx.com/voice.mp4",
            "https://169.254.169.254/latest/meta-data",
            "https://[::1/",
        ],
    )
    def test_only_https_meta_hosts_are_fetched(self, address: str) -> None:
        transport, seen = recording(lambda request: httpx.Response(200))
        fetcher = MetaPageMediaFetcherAdapter(MetaMediaClient(transport=transport))

        with pytest.raises(MediaUnavailableError):
            fetcher.fetch(request_for(ChannelKind.MESSENGER, address))
        assert seen == []

    @pytest.mark.parametrize(
        ("status", "error"),
        [(404, MediaUnavailableError), (410, MediaUnavailableError),
         (503, ExternalServiceError)],
    )
    def test_cdn_errors(self, status: int, error: type[Exception]) -> None:
        transport, _ = recording(lambda request: httpx.Response(status))
        fetcher = MetaPageMediaFetcherAdapter(MetaMediaClient(transport=transport))
        with pytest.raises(error):
            fetcher.fetch(
                request_for(ChannelKind.MESSENGER, "https://cdn.fbsbx.com/v/a.mp4")
            )

    def test_a_declared_length_over_the_cap_stops_before_the_body(self) -> None:
        transport, _ = recording(
            lambda request: httpx.Response(
                200, content=b"x", headers={"Content-Length": str(int(LIMIT) * 2)}
            )
        )
        fetcher = MetaPageMediaFetcherAdapter(MetaMediaClient(transport=transport))
        with pytest.raises(MediaTooLargeError):
            fetcher.fetch(
                request_for(ChannelKind.MESSENGER, "https://cdn.fbsbx.com/v/a.mp4")
            )


def test_the_router_sends_each_channel_to_its_fetcher() -> None:
    transport, seen = recording(lambda request: httpx.Response(200, content=b"ok"))
    page = MetaPageMediaFetcherAdapter(MetaMediaClient(transport=transport))
    router = RoutingChannelMediaFetcherAdapter({ChannelKind.MESSENGER: page})

    fetched = router.fetch(
        request_for(ChannelKind.MESSENGER, "https://cdn.fbsbx.com/v/a.jpg")
    )
    assert fetched.content == b"ok"
    assert len(seen) == 1

    with pytest.raises(MediaUnavailableError):
        router.fetch(request_for(ChannelKind.WEB_CHAT, "anything"))
