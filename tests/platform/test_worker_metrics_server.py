"""A worker's metrics page: the token or nothing, on its own port."""

import socket
from collections.abc import Iterator

import httpx
import pytest

from app.gateways.metrics.worker_metrics_server import WorkerMetricsServer
from app.schemas.typings.observability.constrained_integers import MetricsPort
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.observability.metrics.metrics_exposition import MetricsPage

METRICS_TOKEN: str = "test-token-0000"  # gitleaks:allow
PAGE: bytes = b"workshop_jobs_died_total 0.0\n"


def free_port() -> MetricsPort:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return MetricsPort(int(probe.getsockname()[1]))


@pytest.fixture
def base_url() -> Iterator[str]:
    server = WorkerMetricsServer(
        free_port(), PlatformSecret(METRICS_TOKEN), lambda: MetricsPage(body=PAGE)
    )
    server.start()
    try:
        yield f"http://127.0.0.1:{server.port}"
    finally:
        server.stop()


def test_the_worker_page_needs_the_token(base_url: str) -> None:
    with httpx.Client(base_url=base_url, trust_env=False) as client:
        anonymous = client.get("/metrics")
        wrong = client.get("/metrics", headers={"Authorization": "Bearer nope"})
        scraped = client.get(
            "/metrics", headers={"Authorization": f"Bearer {METRICS_TOKEN}"}
        )
        elsewhere = client.get(
            "/healthz", headers={"Authorization": f"Bearer {METRICS_TOKEN}"}
        )

    assert anonymous.status_code == 401
    assert anonymous.headers["www-authenticate"] == "Bearer"
    assert wrong.status_code == 401
    assert scraped.status_code == 200
    assert scraped.content == PAGE
    assert scraped.headers["content-type"].startswith("text/plain")
    assert elsewhere.status_code == 404
