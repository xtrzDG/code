"""
The providers a game day breaks, served by the test on 127.0.0.1:

- `/meta/...`: Meta's Graph API. Up, it accepts every message
  (`{"messages": [{"id": "wamid.chaos-N"}]}`); black-holed, it takes the
  request and never answers, like a host whose packets vanish.
- `/openai/v1/responses`: OpenAI's Responses API. It answers with one
  assistant message after `llm_delay_seconds` (30 s for the latency game
  day, 0 otherwise).

The worker's clients point here (`chaos_process.py`, CHAOS_PROVIDER_URL)
and give up after their own timeouts: nothing in the app knows it is a
test.
"""

import json
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

# No number, price or promise: the reply guard lets it through as it is.
REPLY_TEXT: str = "Здравствуйте! Сейчас уточню у администратора и сразу отвечу."
# A black-holed request is held at most this long (the client left by then).
HOLD_SECONDS: float = 60.0


class ProviderState:
    """What the providers do now; the test flips it."""

    def __init__(self) -> None:
        self.is_meta_black_holed: bool = False
        self.llm_delay_seconds: float = 0.0
        self.meta_messages: int = 0
        self.llm_calls: int = 0
        self._guard = threading.Lock()
        self.released = threading.Event()

    def count(self, kind: str) -> int:
        with self._guard:
            if kind == "meta":
                self.meta_messages += 1
                return self.meta_messages
            self.llm_calls += 1
            return self.llm_calls


def openai_body(text: str) -> dict[str, Any]:
    return {
        "id": "resp_chaos",
        "object": "response",
        "created_at": int(time.time()),
        "model": "gpt-5-mini-2025-08-07",
        "status": "completed",
        "error": None,
        "incomplete_details": None,
        "output": [
            {
                "type": "message",
                "id": "msg_chaos",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            }
        ],
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
        "usage": {
            "input_tokens": 900,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens": 40,
            "output_tokens_details": {"reasoning_tokens": 0},
            "total_tokens": 940,
        },
    }


def build_handler(state: ProviderState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            del format, args

        def do_GET(self) -> None:  # noqa: N802 - http.server's name
            self._answer({"id": "chaos", "name": "Chaos"})

        def do_POST(self) -> None:  # noqa: N802 - http.server's name
            length = int(self.headers.get("Content-Length") or 0)
            self.rfile.read(length)
            if self.path.startswith("/openai/"):
                state.count("llm")
                state.released.wait(timeout=state.llm_delay_seconds)
                self._answer(openai_body(REPLY_TEXT))
                return

            if state.is_meta_black_holed:
                # Take the request and say nothing: the client times out.
                state.released.wait(timeout=HOLD_SECONDS)
                return

            number = state.count("meta")
            self._answer(
                {
                    "messaging_product": "whatsapp",
                    "contacts": [],
                    "messages": [{"id": f"wamid.chaos-{number}"}],
                    "success": True,
                }
            )

        def _answer(self, body: dict[str, Any]) -> None:
            payload = json.dumps(body).encode()
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except BrokenPipeError, ConnectionResetError:
                pass  # The client gave up first.

    return Handler


@contextmanager
def fake_providers() -> Generator[tuple[str, ProviderState]]:
    """The providers' base URL and the switch board, for one world."""

    state = ProviderState()
    server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(state))
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", state
    finally:
        state.released.set()
        server.shutdown()
        server.server_close()
