"""
A worker's metrics page: GET /metrics on WORKER_METRICS_PORT, served by a
small HTTP server on a thread of its own (a worker has no web framework),
with the same bearer token as the API's (METRICS_TOKEN). Anything else
gets 404; a scrape without the token 401. Off unless both are set.
"""

import logging
import threading
from collections.abc import Callable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.schemas.typings.observability.constrained_integers import MetricsPort
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.observability.metrics.metrics_access import carries_metrics_token
from app.utilities.observability.metrics.metrics_exposition import MetricsPage

LOGGER: logging.Logger = logging.getLogger(__name__)
METRICS_PATH: str = "/metrics"
# Every interface of the worker's container; the page needs the token.
ALL_INTERFACES: str = ""

type MetricsRenderer = Callable[[], MetricsPage]


class WorkerMetricsServer:
    """The worker's metrics page on its own port, until `stop`."""

    def __init__(
        self,
        port: MetricsPort,
        token: PlatformSecret,
        render: MetricsRenderer,
    ) -> None:
        self._server: ThreadingHTTPServer = ThreadingHTTPServer(
            (ALL_INTERFACES, int(port)), metrics_request_handler(token, render)
        )
        self._server.daemon_threads = True
        self._thread: threading.Thread = threading.Thread(
            target=self._server.serve_forever,
            name="worker-metrics",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()
        LOGGER.info("Worker metrics served on port %d", self.port)

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()


def metrics_request_handler(
    token: PlatformSecret, render: MetricsRenderer
) -> type[BaseHTTPRequestHandler]:
    """The request handler class of one server: its token and its page."""

    class MetricsRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - the name http.server calls
            if self.path.split("?", 1)[0] != METRICS_PATH:
                self._answer(HTTPStatus.NOT_FOUND, b"Not found.\n")
                return

            if not carries_metrics_token(self.headers.get("Authorization"), token):
                self._answer(HTTPStatus.UNAUTHORIZED, b"A metrics token is needed.\n")
                return

            page: MetricsPage = render()
            self._answer(HTTPStatus.OK, page.body, page.content_type)

        def _answer(
            self,
            status: HTTPStatus,
            body: bytes,
            content_type: str = "text/plain; charset=utf-8",
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            if status is HTTPStatus.UNAUTHORIZED:
                self.send_header("WWW-Authenticate", "Bearer")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            # Scrapes are not worth a log line each (the API's access log
            # skips them too).
            del format, args

    return MetricsRequestHandler
