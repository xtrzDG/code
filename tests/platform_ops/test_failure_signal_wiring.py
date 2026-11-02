"""
The HTTP application counts the failure signals of the platform health
alerts (LOG-04): a webhook refused by the admission or by its verifier, an
unexpected database failure, and a request slower than 2 s; probes and an
application without signals count nothing.
"""

from types import SimpleNamespace

import psycopg
import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.gateways.failure_signals import FailureSignals
from app.gateways.http.application import build_http_application
from app.gateways.http.middleware import request_telemetry_middleware
from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from tests.platform_ops.failure_signal_doubles import CountedSignals, NoErrorReports

META_WEBHOOK: str = "/v1/channels/meta/webhook"
SIGNED_META: dict[str, str] = {"X-Hub-Signature-256": "sha256=" + "ab" * 32}


def build_application(signals: FailureSignals | None) -> FastAPI:
    router = APIRouter()

    @router.post(META_WEBHOOK)
    def meta_webhook() -> None:
        raise AuthenticationRequiredError("The signature does not match.")

    @router.get("/v1/broken")
    def broken() -> None:
        raise psycopg.OperationalError("server closed the connection")

    @router.get("/v1/fine")
    def fine() -> dict[str, bool]:
        return {"ok": True}

    return build_http_application(
        routers=[router],
        error_reporter=NoErrorReports(),
        cors_allowed_origins=[],
        failure_signals=signals,
    )


def client_counting(counted: CountedSignals) -> TestClient:
    signals = FailureSignals(counted, run_later=lambda work: work())
    return TestClient(build_application(signals), raise_server_exceptions=False)


def test_a_delivery_the_admission_refuses_is_counted() -> None:
    counted = CountedSignals()

    response = client_counting(counted).post(META_WEBHOOK, content=b"{}")

    assert response.status_code == 401
    assert counted.calls == [PlatformSignal.WEBHOOK_REFUSED]


def test_a_delivery_its_verifier_refuses_is_counted() -> None:
    counted = CountedSignals()

    response = client_counting(counted).post(
        META_WEBHOOK, content=b"{}", headers=SIGNED_META
    )

    assert response.status_code == 401
    assert counted.calls == [PlatformSignal.WEBHOOK_REFUSED]


def test_an_unexpected_database_failure_is_counted() -> None:
    counted = CountedSignals()

    response = client_counting(counted).get("/v1/broken")

    assert response.status_code == 500
    assert counted.calls == [PlatformSignal.DATABASE_ERROR]


class SlowClock:
    """perf_counter of a request that takes `seconds`."""

    def __init__(self, seconds: float) -> None:
        self.readings: list[float] = [100.0, 100.0 + seconds]

    def perf_counter(self) -> float:
        return self.readings.pop(0) if len(self.readings) > 1 else self.readings[0]


@pytest.mark.parametrize(
    ("path", "seconds", "signals"),
    [
        ("/v1/fine", 2.5, [PlatformSignal.SLOW_API_REQUEST]),
        ("/v1/fine", 0.3, []),
        ("/healthz", 9.0, []),
    ],
)
def test_slow_requests_are_counted_but_not_probes(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    seconds: float,
    signals: list[PlatformSignal],
) -> None:
    counted = CountedSignals()
    client = client_counting(counted)
    monkeypatch.setattr(
        request_telemetry_middleware,
        "time",
        SimpleNamespace(perf_counter=SlowClock(seconds).perf_counter),
    )

    client.get(path)

    assert counted.calls == signals


def test_an_application_without_signals_counts_nothing() -> None:
    client = TestClient(build_application(None), raise_server_exceptions=False)

    assert client.post(META_WEBHOOK, content=b"{}").status_code == 401
    assert client.get("/v1/broken").status_code == 500
