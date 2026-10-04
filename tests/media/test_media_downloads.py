"""
Downloading customer files from the platforms: WhatsApp's Graph lookup and
download, Telegram's getFile, Messenger and Instagram CDN addresses; size
caps before and while downloading, and errors that never carry a token.
"""

import httpx
import pytest

from app.adapters.media.telegram_media_fetcher_adapter import (
    TelegramMediaFetcherAdapter,
)
from app.adapters.media.whatsapp_media_fetcher_adapter import (
    WhatsAppMediaFetcherAdapter,
)
from app.clients.meta.meta_media_client import MetaMediaClient
from app.clients.telegram.telegram_file_client import TelegramFileClient
from app.schemas.constants.channels import ChannelKind
from app.schemas.exceptions.application_errors import (
    ChannelCredentialRejectedError,
    ExternalServiceError,
)
from app.schemas.exceptions.media_errors import (
    MediaTooLargeError,
    MediaUnavailableError,
)
from tests.channels.channels_settings import WHATSAPP_SYSTEM_TOKEN, build_settings
from tests.media.download_helpers import (
    BOT_TOKEN,
    CDN_URL,
    LIMIT,
    Handler,
    recording,
    request_for,
)
from tests.media.media_fakes import jpeg_bytes, ogg_opus_bytes


class TestWhatsApp:
    def fetcher(
        self, handler: Handler
    ) -> tuple[WhatsAppMediaFetcherAdapter, list[httpx.Request]]:
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
    def fetcher(
        self, handler: Handler
    ) -> tuple[TelegramMediaFetcherAdapter, list[httpx.Request]]:
        transport, seen = recording(handler)
        return TelegramMediaFetcherAdapter(
            TelegramFileClient(transport=transport)
        ), seen

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
            (
                401,
                {"ok": False, "error_code": 401, "description": "Unauthorized"},
                ChannelCredentialRejectedError,
            ),
            (
                400,
                {"ok": False, "error_code": 400, "description": "file is too big"},
                MediaUnavailableError,
            ),
            (
                502,
                {"ok": False, "error_code": 502, "description": "Bad Gateway"},
                ExternalServiceError,
            ),
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
