"""An SSE response that ends as soon as the client goes away."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import suppress

import anyio
from starlette.responses import StreamingResponse
from starlette.types import Receive, Scope, Send

from app.gateways.http.live_events.event_stream_format import EVENT_STREAM_MEDIA_TYPE

# Never cached or transformed (compression would buffer the stream) by a
# proxy, and nginx-style proxies pass every chunk on at once.
EVENT_STREAM_HEADERS: dict[str, str] = {
    "Cache-Control": "no-cache, no-transform",
    "X-Accel-Buffering": "no",
}


class EventStreamResponse(StreamingResponse):
    """
    Streams `chunks` while it also waits for the client's disconnect: a
    closed tab ends the stream at once (not only at the next heartbeat), so
    its slot of the person's stream limit is free again. `on_close` runs
    exactly once whatever ends the stream, also when it never started.
    """

    def __init__(
        self,
        chunks: AsyncIterator[bytes],
        on_close: Callable[[], None],
    ) -> None:
        super().__init__(
            chunks, media_type=EVENT_STREAM_MEDIA_TYPE, headers=EVENT_STREAM_HEADERS
        )
        self._chunks: AsyncIterator[bytes] = chunks
        self._on_close: Callable[[], None] = on_close

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        del scope
        try:
            async with anyio.create_task_group() as task_group:

                async def stream_until_done() -> None:
                    # OSError: the client went away while a chunk was written.
                    with suppress(OSError):
                        await self.stream_response(send)
                    task_group.cancel_scope.cancel()

                task_group.start_soon(stream_until_done)
                await self.listen_for_disconnect(receive)
                task_group.cancel_scope.cancel()
        finally:
            self._on_close()
            await self._close_chunks()

    async def _close_chunks(self) -> None:
        # An async generator left suspended runs its cleanup now, not when
        # the garbage collector finds it.
        aclose: Callable[[], Awaitable[None]] | None = getattr(
            self._chunks, "aclose", None
        )
        if aclose is not None:
            await aclose()
