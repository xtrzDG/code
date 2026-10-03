"""
Messenger and Instagram attachments are downloaded from Meta's CDN only:
https addresses on Meta hosts, without a token, within the size cap.
"""

import httpx
import pytest

from app.adapters.media.meta_page_media_fetcher_adapter import (
    MetaPageMediaFetcherAdapter,
)
from app.adapters.media.routing_channel_media_fetcher_adapter import (
    RoutingChannelMediaFetcherAdapter,
)
from app.clients.meta.meta_media_client import MetaMediaClient
from app.schemas.constants.channels import ChannelKind
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.media_errors import (
    MediaTooLargeError,
    MediaUnavailableError,
)
from tests.media.download_helpers import LIMIT, recording, request_for
from tests.media.media_fakes import ogg_opus_bytes


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
        [
            (404, MediaUnavailableError),
            (410, MediaUnavailableError),
            (503, ExternalServiceError),
        ],
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
