"""A local stand-in of the deployed API and cabinet for the smoke script tests."""

import json
import threading
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import cast

BUSINESS_ID: str = "business_8a4c3f52-1d1e-4c47-9d4d-2b1f0f7f6c11"
WIDGET_PREFIX: str = f"/v1/widget/{BUSINESS_ID}"
REPLY: str = (
    "Thank you for your message! This is the test assistant of a staging server."
)


@dataclass
class FakeDeployment:
    """How the fake answers; tests change what a broken release would."""

    widget_script: str = "(function () { window.workshopWidget = true; })();"
    configured_channels: list[str] = field(default_factory=lambda: ["email"])
    reply_inline: bool = True
    reply_text: str = REPLY
    is_ready: bool = True
    polls: int = 0
    posted: list[dict[str, object]] = field(default_factory=list[dict[str, object]])


def build_handler(deployment: FakeDeployment) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path: str = self.path.split("?", 1)[0]
            if path == "/healthz":
                self.answer(200, {"status": "ok"})
            elif path == "/readyz":
                self.answer(
                    200 if deployment.is_ready else 503,
                    {"status": "ready" if deployment.is_ready else "not_ready"},
                )
            elif path == "/widget.js":
                self.answer_text(200, deployment.widget_script, "text/javascript")
            elif path == "/v1/auth/login-options":
                self.answer(
                    200, {"configured_channels": deployment.configured_channels}
                )
            elif path == "/cabinet/login":
                self.answer_text(200, "<html>login</html>", "text/html")
            elif path == f"{WIDGET_PREFIX}/config":
                self.answer(200, {"business_name": "Smoke"})
            elif path == f"{WIDGET_PREFIX}/messages":
                deployment.polls += 1
                self.answer(200, self.polled_messages())
            else:
                self.answer(404, {"error": "not_found"})

        def do_POST(self) -> None:
            length: int = int(self.headers.get("Content-Length", "0"))
            body: object = json.loads(self.rfile.read(length) or b"{}")
            if self.path != f"{WIDGET_PREFIX}/messages" or not isinstance(body, dict):
                self.answer(404, {"error": "not_found"})
                return

            deployment.posted.append(cast(dict[str, object], body))
            text: str | None = (
                deployment.reply_text if deployment.reply_inline else None
            )
            self.answer(200, {"text": text, "cursor": "message_1"})

        def polled_messages(self) -> dict[str, object]:
            if deployment.polls < 2:
                return {"items": [], "cursor": "message_1"}

            return {
                "items": [
                    {"author": "staff", "text": "Hi from staff"},
                    {"author": "assistant", "text": deployment.reply_text},
                ],
                "cursor": "message_3",
            }

        def answer(self, status: int, body: object) -> None:
            self.answer_text(status, json.dumps(body), "application/json")

        def answer_text(self, status: int, text: str, content_type: str) -> None:
            encoded: bytes = text.encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            del format, args

    return Handler


@contextmanager
def running_deployment(deployment: FakeDeployment) -> Generator[str]:
    """The fake on a free local port; yields its base URL."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(deployment))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
