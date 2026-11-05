"""
The upload route streams the body under one of the process's upload
places: a second upload while the only place is taken gets 429 at once,
a photo is read only up to the photo cap (before, up to the larger voice
note cap, as the type was not known until the whole body was read), a
type the chat does not take is refused before its file is read, and a
body that trickles is refused in time with its place given back.
"""

import asyncio
import threading
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx

from tests.channels.channels_settings import build_settings
from tests.channels.multipart_bodies import BOUNDARY, FORM, part_head
from tests.channels.test_widget import SESSION_KEY
from tests.channels.widget_upload_bed import SMALL_MEDIA_LIMITS, WidgetUploadBed
from tests.media.upload_files import png_photo

CHUNK: int = 4 * 1024
CLOSING: bytes = f"\r\n--{BOUNDARY}--\r\n".encode()
# The bed's caps: photos 64 KiB, voice notes 128 KiB.
PHOTO_CAP: int = 64 * 1024
VOICE_CAP: int = 128 * 1024


class BlockingAccept:
    """The accept operator, held inside its upload until released."""

    def __init__(self, operator: Any) -> None:
        self.operator: Any = operator
        self.entered = threading.Event()
        self.release = threading.Event()

    def operate(self, input_data: Any) -> Any:
        self.entered.set()
        assert self.release.wait(timeout=30)
        return self.operator.operate(input_data)


class StreamedBody:
    """A head, then `file_bytes` zeros in small chunks, counting what was sent."""

    def __init__(self, head: bytes, file_bytes: int, hang: bool = False) -> None:
        self.head: bytes = head
        self.file_bytes: int = file_bytes
        self.hang: bool = hang
        self.file_bytes_sent: int = 0

    async def chunks(self) -> AsyncIterator[bytes]:
        yield self.head
        while self.file_bytes_sent < self.file_bytes:
            size = min(CHUNK, self.file_bytes - self.file_bytes_sent)
            self.file_bytes_sent += size
            yield bytes(size)
        if self.hang:
            await asyncio.Event().wait()
        yield CLOSING


def stream_upload(bed: WidgetUploadBed, body: StreamedBody) -> httpx.Response:
    async def call() -> httpx.Response:
        transport = httpx.ASGITransport(app=bed.client.app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.post(
                f"/v1/widget/{bed.business.id}/attachments",
                content=body.chunks(),
                headers={"Content-Type": FORM, "X-Widget-Session-Key": SESSION_KEY},
            )

    return asyncio.run(call())


def reason_code(response: httpx.Response | Any) -> str:
    code: str = response.json()["reasons"][0]["code"]
    return code


class TestPlaces:
    def test_an_upload_while_the_only_place_is_taken_gets_429(self) -> None:
        blocking: list[BlockingAccept] = []

        def hold_inside(operator: Any) -> BlockingAccept:
            blocking.append(BlockingAccept(operator))
            return blocking[0]

        bed = WidgetUploadBed(
            build_settings(**SMALL_MEDIA_LIMITS, MEDIA_MAX_CONCURRENT_UPLOADS="1"),
            wrap_accept=hold_inside,
        )
        [accept] = blocking
        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(bed.upload, png_photo(), "image/png")
            assert accept.entered.wait(timeout=30)

            busy = bed.upload(png_photo(), "image/png")
            accept.release.set()

            assert first.result().status_code == 201
        assert busy.status_code == 429
        assert int(busy.headers["Retry-After"]) > 0
        assert reason_code(busy) == "too_many_uploads_at_once"
        # The place came back with the first upload's answer.
        assert bed.upload(png_photo(), "image/png").status_code == 201


class TestStreaming:
    def test_a_photo_is_read_only_up_to_the_photo_cap(self) -> None:
        bed = WidgetUploadBed()
        body = StreamedBody(part_head(content_type="image/jpeg"), 4 * VOICE_CAP)

        response = stream_upload(bed, body)

        assert response.status_code == 422
        assert reason_code(response) == "file_too_large"
        assert response.json()["reasons"][0]["details"] == [str(PHOTO_CAP)]
        assert body.file_bytes_sent <= PHOTO_CAP + 2 * CHUNK

    def test_a_type_the_chat_does_not_take_is_refused_before_its_file(
        self,
    ) -> None:
        bed = WidgetUploadBed()
        body = StreamedBody(part_head(content_type="image/gif"), 4 * CHUNK)

        response = stream_upload(bed, body)

        assert response.status_code == 422
        assert reason_code(response) == "unsupported_type"
        assert body.file_bytes_sent <= CHUNK

    def test_a_body_that_trickles_is_refused_and_its_place_given_back(
        self,
    ) -> None:
        bed = WidgetUploadBed(
            build_settings(**SMALL_MEDIA_LIMITS, MEDIA_MAX_CONCURRENT_UPLOADS="1"),
            upload_read_seconds=0.2,
        )
        body = StreamedBody(part_head(content_type="image/png"), CHUNK, hang=True)

        response = stream_upload(bed, body)

        assert response.status_code == 422
        assert reason_code(response) == "upload_too_slow"
        assert bed.upload(png_photo(), "image/png").status_code == 201
        assert bed.testbed.media_storage.files != {}
