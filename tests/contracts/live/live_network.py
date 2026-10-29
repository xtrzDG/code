"""
The real network for the live smoke (tests/contracts/live): every exchange
is kept so the provider's real answer can be checked against the vendored
specification, and a provider is skipped while its sandbox secrets are not
set. Nothing here runs unless CONTRACTS_LIVE=1 (the nightly workflow).
"""

import json
import os
from pathlib import Path

import httpx
import pytest

LIVE_SWITCH: str = "CONTRACTS_LIVE"
# Set locally to keep every JSON answer (tests/contracts/README.md,
# "Recording sandbox payloads"); never in CI.
RECORD_DIRECTORY_VARIABLE: str = "CONTRACTS_RECORD_DIR"
TIMEOUT_SECONDS: float = 30.0


def is_live() -> bool:
    return os.environ.get(LIVE_SWITCH) == "1"


def sandbox_secrets(*names: str) -> list[str]:
    """The named sandbox secrets, or a skip naming the missing ones."""

    values: list[str] = [os.environ.get(name, "").strip() for name in names]
    missing: list[str] = [
        name for name, value in zip(names, values, strict=True) if not value
    ]
    if missing:
        pytest.skip(f"Sandbox secrets not set: {', '.join(missing)}")

    return values


class RecordingNetwork(httpx.BaseTransport):
    """The real network; each exchange is kept with its body read."""

    def __init__(self) -> None:
        self._network: httpx.HTTPTransport = httpx.HTTPTransport(retries=1)
        self.exchanges: list[tuple[httpx.Request, httpx.Response]] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        response: httpx.Response = self._network.handle_request(request)
        response.read()
        self.exchanges.append((request, response))
        keep_answer(response, len(self.exchanges))
        return response

    def close(self) -> None:
        self._network.close()

    def last(self) -> tuple[httpx.Request, httpx.Response]:
        return self.exchanges[-1]


def checked_answer(response: httpx.Response) -> object:
    """
    The JSON answer of a successful call. A failure names the status only:
    sandbox URLs and answers may carry a token.
    """

    assert response.is_success, f"The provider answered HTTP {response.status_code}."
    return response.json()


def keep_answer(response: httpx.Response, number: int) -> None:
    """Write a JSON answer to CONTRACTS_RECORD_DIR, when it is set."""

    directory: str = os.environ.get(RECORD_DIRECTORY_VARIABLE, "").strip()
    if not directory or "json" not in response.headers.get("content-type", ""):
        return

    test_name: str = os.environ.get("PYTEST_CURRENT_TEST", "live").split("::")[-1]
    path: Path = Path(directory) / f"{test_name.split(' ')[0]}-{number}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(response.json(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
