"""
The booking round trip of production's synthetic checks
(.github/workflows/synthetics.yml), through the public API with the
monitoring business's API key (MONITORING_API_KEY):

    MONITORING_API_KEY=awk_... uv run --no-project python -m \\
        scripts.synthetic_booking https://api.example.com

1. GET  /v1/public-api/me                      the key opens the monitoring business
2. POST /v1/public-api/bookings                a booking for one, 28 days ahead
                                               (same weekday) at 12:00, with an
                                               Idempotency-Key of this run
3. GET  /v1/public-api/bookings/{id}           it is stored
4. POST /v1/public-api/bookings/{id}/cancel    it is cancelled again
5. GET  /v1/public-api/bookings/{id}           and stays cancelled

The monitoring business must take a booking for one at that time every day.
A booking that could not be cancelled is named, to cancel it by hand. Exit
codes: 0 every step passed, 1 a step failed, 2 wrong usage (no key, not an
https address).
"""

import argparse
import datetime
import http.client
import json
import os
import sys
from collections.abc import Callable, Sequence
from typing import Any, cast
from urllib.parse import urlsplit

EXIT_PASSED: int = 0
EXIT_FAILED: int = 1
EXIT_USAGE: int = 2
KEY_VARIABLE: str = "MONITORING_API_KEY"
RUN_VARIABLE: str = "GITHUB_RUN_ID"
DAYS_AHEAD: int = 28
BOOKING_TIME: str = "12:00"
TIMEOUT_SECONDS: float = 20.0
CANCELLED: str = "cancelled"
CONTACT_NAME: str = "Synthetic check"


class StepFailed(Exception):
    """A step of the round trip did not answer as expected."""


# (method, address, body, headers) -> (status, body): https only.
type Transport = Callable[[str, str, bytes | None, dict[str, str]], tuple[int, bytes]]


def https_transport(
    method: str, address: str, body: bytes | None, headers: dict[str, str]
) -> tuple[int, bytes]:
    parts = urlsplit(address)
    connection = http.client.HTTPSConnection(parts.netloc, timeout=TIMEOUT_SECONDS)
    try:
        connection.request(method, parts.path, body=body, headers=headers)
        answer = connection.getresponse()
        return answer.status, answer.read()
    finally:
        connection.close()


class Api:
    def __init__(self, base_url: str, key: str, transport: Transport) -> None:
        self.base_url = base_url.rstrip("/")
        self.key = key
        self.transport = transport

    def call(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        try:
            status, content = self.transport(
                method,
                f"{self.base_url}{path}",
                None if body is None else json.dumps(body).encode(),
                {
                    "Authorization": f"Bearer {self.key}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    **(headers or {}),
                },
            )
        except (OSError, http.client.HTTPException) as error:
            raise StepFailed(f"{method} {path}: no answer ({error})") from error
        return status, parse(content)


def parse(content: bytes) -> dict[str, Any]:
    try:
        document: object = json.loads(content or b"{}")
    except ValueError:
        return {}
    return cast(dict[str, Any], document) if isinstance(document, dict) else {}


def expect(step: str, status: int, wanted: int, body: dict[str, Any]) -> None:
    if status != wanted:
        raise StepFailed(f"{step}: HTTP {status}, expected {wanted} ({body})")
    print(f"ok    {step}")


def booking_request(today: datetime.date) -> dict[str, Any]:
    return {
        "contact_name": CONTACT_NAME,
        "date": (today + datetime.timedelta(days=DAYS_AHEAD)).isoformat(),
        "time": BOOKING_TIME,
        "party_size": 1,
        "notes": "Synthetic check of production; cancelled at once.",
    }


def round_trip(api: Api, today: datetime.date, run_id: str) -> None:
    status, me = api.call("GET", "/v1/public-api/me")
    expect("the monitoring key opens its business", status, 200, me)
    status, created = api.call(
        "POST",
        "/v1/public-api/bookings",
        booking_request(today),
        {"Idempotency-Key": f"synthetic-booking-{run_id}"},
    )
    expect("a booking is created", status, 201, created)
    booking_id = str(created.get("id") or "")
    if not booking_id:
        raise StepFailed(f"the created booking has no id ({created})")
    path = f"/v1/public-api/bookings/{booking_id}"
    try:
        status, stored = api.call("GET", path)
        expect("the booking is stored", status, 200, stored)
        status, cancelled = api.call("POST", f"{path}/cancel", {})
        expect("the booking is cancelled", status, 200, cancelled)
        status, after = api.call("GET", path)
        expect("it stays cancelled", status, 200, after)
        if after.get("status") != CANCELLED:
            raise StepFailed(f"the booking's status is {after.get('status')!r}")
    except StepFailed:
        print(f"::error::Cancel booking {booking_id} by hand.", file=sys.stderr)
        raise


def main(
    arguments: Sequence[str] | None = None, transport: Transport = https_transport
) -> int:
    parser = argparse.ArgumentParser(description="Production's booking round trip.")
    parser.add_argument("api_url", help="the production API's https address")
    parsed = parser.parse_args(arguments)
    key = os.environ.get(KEY_VARIABLE, "")
    address = urlsplit(parsed.api_url)
    if not key or address.scheme != "https" or not address.hostname:
        print(
            f"::error::Usage: {KEY_VARIABLE}=awk_... python -m"
            " scripts.synthetic_booking https://<production API>",
            file=sys.stderr,
        )
        return EXIT_USAGE
    run_id = os.environ.get(RUN_VARIABLE) or datetime.datetime.now(
        datetime.UTC
    ).strftime("%Y%m%d%H%M%S")
    try:
        round_trip(
            Api(parsed.api_url, key, transport),
            datetime.datetime.now(datetime.UTC).date(),
            run_id,
        )
    except StepFailed as error:
        print(f"FAIL  {error}", file=sys.stderr)
        return EXIT_FAILED
    return EXIT_PASSED


if __name__ == "__main__":
    sys.exit(main())
