"""
Production's synthetic booking round trip (scripts/synthetic_booking.py, run
by .github/workflows/synthetics.yml): with the monitoring key it creates a
booking 28 days ahead under an Idempotency-Key of the run, reads it, cancels
it and checks it stays cancelled; a step that answers otherwise fails and
names the booking left behind; no key or no https address is wrong usage.
Nothing is written unless production's own API contract (the `release`
branch's web/openapi.json) has every operation of the round trip.
"""

import datetime
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from scripts.synthetic_booking import EXIT_FAILED, EXIT_PASSED, EXIT_USAGE, main

API: str = "https://api.workshop.test"
BOOKING_ID: str = "booking_8a4c3f52-1d1e-4c47-9d4d-2b1f0f7f6c11"
CANCEL: str = "/v1/public-api/bookings/{booking_id}/cancel"
OPERATIONS: dict[str, list[str]] = {
    "/v1/public-api/me": ["get"],
    "/v1/public-api/bookings": ["get", "post"],
    "/v1/public-api/bookings/{booking_id}": ["get"],
    CANCEL: ["post"],
}


@pytest.fixture
def contract(tmp_path: Path) -> Path:
    """Production's OpenAPI document with every operation of the round trip."""

    return write_contract(tmp_path, OPERATIONS)


def write_contract(directory: Path, operations: dict[str, list[str]]) -> Path:
    path = directory / "openapi.json"
    paths: dict[str, dict[str, dict[str, Any]]] = {
        route: {method: {"responses": {}} for method in methods}
        for route, methods in operations.items()
    }
    path.write_text(json.dumps({"openapi": "3.1.0", "paths": paths}), "utf-8")
    return path


@dataclass
class FakeApi:
    """The public API of a monitoring business; tests break one answer."""

    status: str = "confirmed"
    broken: dict[str, int] = field(default_factory=dict[str, int])
    calls: list[tuple[str, str, Any, dict[str, str]]] = field(
        default_factory=list[tuple[str, str, Any, dict[str, str]]]
    )

    def __call__(
        self, method: str, address: str, body: bytes | None, headers: dict[str, str]
    ) -> tuple[int, bytes]:
        path = address.removeprefix(API)
        self.calls.append((method, path, json.loads(body) if body else None, headers))
        step = f"{method} {path}"
        if step in self.broken:
            return self.broken[step], b'{"detail": "broken"}'
        booking = {"id": BOOKING_ID, "status": self.status}
        if step == "GET /v1/public-api/me":
            return 200, b'{"business": {"name": "Monitoring"}}'
        if step == "POST /v1/public-api/bookings":
            return 201, json.dumps(booking).encode()
        if step == f"POST /v1/public-api/bookings/{BOOKING_ID}/cancel":
            self.status = "cancelled"
            return 200, json.dumps({**booking, "status": "cancelled"}).encode()
        if step == f"GET /v1/public-api/bookings/{BOOKING_ID}":
            return 200, json.dumps(booking).encode()
        return 404, b"{}"


def check(
    monkeypatch: pytest.MonkeyPatch, api: FakeApi, contract: Path, address: str = API
) -> tuple[int, str, str]:
    monkeypatch.setenv("MONITORING_API_KEY", "awk_test_key")  # gitleaks:allow
    monkeypatch.setenv("GITHUB_RUN_ID", "4242")
    output, errors = io.StringIO(), io.StringIO()
    with redirect_stdout(output), redirect_stderr(errors):
        code = main(["--contract", str(contract), address], transport=api)
    return code, output.getvalue(), errors.getvalue()


def test_the_round_trip_creates_and_cancels_one_booking(
    monkeypatch: pytest.MonkeyPatch, contract: Path
) -> None:
    api = FakeApi()
    code, output, _ = check(monkeypatch, api, contract)

    assert code == EXIT_PASSED
    assert [f"{method} {path}" for method, path, _, _ in api.calls] == [
        "GET /v1/public-api/me",
        "POST /v1/public-api/bookings",
        f"GET /v1/public-api/bookings/{BOOKING_ID}",
        f"POST /v1/public-api/bookings/{BOOKING_ID}/cancel",
        f"GET /v1/public-api/bookings/{BOOKING_ID}",
    ]
    _, _, request, headers = api.calls[1]
    ahead = datetime.datetime.now(datetime.UTC).date() + datetime.timedelta(days=28)
    assert request["date"] == ahead.isoformat() and request["time"] == "12:00"
    assert request["party_size"] == 1
    assert headers["Idempotency-Key"] == "synthetic-booking-4242"
    assert all(each[3]["Authorization"] == "Bearer awk_test_key" for each in api.calls)
    assert output.count("ok    ") == 5


def test_a_refused_key_fails_before_anything_is_written(
    monkeypatch: pytest.MonkeyPatch, contract: Path
) -> None:
    api = FakeApi(broken={"GET /v1/public-api/me": 401})
    code, _, errors = check(monkeypatch, api, contract)

    assert code == EXIT_FAILED
    assert "HTTP 401, expected 200" in errors
    assert len(api.calls) == 1


def test_a_failed_cancel_names_the_booking_left_behind(
    monkeypatch: pytest.MonkeyPatch, contract: Path
) -> None:
    api = FakeApi(broken={f"POST /v1/public-api/bookings/{BOOKING_ID}/cancel": 404})
    code, _, errors = check(monkeypatch, api, contract)

    assert code == EXIT_FAILED
    assert f"Cancel booking {BOOKING_ID} by hand." in errors


def test_a_booking_that_does_not_stay_cancelled_fails(
    monkeypatch: pytest.MonkeyPatch, contract: Path
) -> None:
    class Uncancelled(FakeApi):
        def __call__(
            self, method: str, address: str, body: bytes | None, headers: dict[str, str]
        ) -> tuple[int, bytes]:
            status, content = super().__call__(method, address, body, headers)
            self.status = "confirmed"
            return status, content

    code, _, errors = check(monkeypatch, Uncancelled(), contract)

    assert code == EXIT_FAILED
    assert "status is 'confirmed'" in errors


def test_no_answer_is_a_failed_step(
    monkeypatch: pytest.MonkeyPatch, contract: Path
) -> None:
    def unreachable(
        method: str, address: str, body: bytes | None, headers: dict[str, str]
    ) -> tuple[int, bytes]:
        raise OSError("connection refused")

    monkeypatch.setenv("MONITORING_API_KEY", "awk_test_key")  # gitleaks:allow
    errors = io.StringIO()
    with redirect_stderr(errors):
        code = main(["--contract", str(contract), API], transport=unreachable)

    assert code == EXIT_FAILED
    assert "no answer (connection refused)" in errors.getvalue()


@pytest.mark.parametrize("address", ["http://api.workshop.test", "api.workshop.test"])
def test_only_an_https_address_is_checked(
    monkeypatch: pytest.MonkeyPatch, contract: Path, address: str
) -> None:
    api = FakeApi()

    assert check(monkeypatch, api, contract, address)[0] == EXIT_USAGE
    assert api.calls == []


def test_no_key_is_wrong_usage(monkeypatch: pytest.MonkeyPatch, contract: Path) -> None:
    monkeypatch.delenv("MONITORING_API_KEY", raising=False)
    api = FakeApi()

    assert main(["--contract", str(contract), API], transport=api) == EXIT_USAGE
    assert api.calls == []


def test_without_a_cancel_route_nothing_is_written(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Production's API cannot cancel yet: a booking made now would stay.
    without_cancel = {
        route: methods for route, methods in OPERATIONS.items() if route != CANCEL
    }
    api = FakeApi()
    code, _, errors = check(monkeypatch, api, write_contract(tmp_path, without_cancel))

    assert code == EXIT_FAILED
    assert api.calls == []
    assert f"lacks POST {CANCEL}" in errors and "no booking was created" in errors


@pytest.mark.parametrize("text", ["not json", "[]", '{"openapi": "3.1.0"}'])
def test_an_unreadable_contract_is_wrong_usage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, text: str
) -> None:
    unreadable = tmp_path / "openapi.json"
    unreadable.write_text(text, encoding="utf-8")
    api = FakeApi()

    assert check(monkeypatch, api, unreadable)[0] == EXIT_USAGE
    assert check(monkeypatch, api, tmp_path / "missing.json")[0] == EXIT_USAGE
    assert api.calls == []
