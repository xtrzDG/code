"""POST /v1/widget/errors: the widget's error beacon, limited, without texts."""

import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.containers.app import AppContainer
from app.main import build_application
from app.utilities.channels.widget_error_limits import PER_ADDRESS_PER_MINUTE
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.e2e.workshop_container import replace_provider

ERRORS_PATH: str = "/v1/widget/errors"
REPORT: dict[str, object] = {
    "kind": "script_error",
    "phase": "poll",
    "business_id": "business_0f8f6bd6-e9b2-4a4c-8b8c-3c1f2a7e9d10",
    "error_name": "TypeError",
    "line": 412,
    "column": 17,
}


def build_client() -> TestClient:
    container = AppContainer()
    replace_provider(container.config.app_settings, assemble_app_settings({}))
    return TestClient(build_application(container))


def send(client: TestClient, report: dict[str, object]) -> int:
    # The widget posts text/plain (no CORS preflight), as sendBeacon does.
    response = client.post(
        ERRORS_PATH,
        content=json.dumps(report),
        headers={"Content-Type": "text/plain;charset=UTF-8"},
    )
    return response.status_code


def test_a_widget_error_is_accepted_and_reported(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = build_client()

    with caplog.at_level(logging.WARNING, logger="app.widget"):
        response = client.post(
            ERRORS_PATH,
            content=json.dumps(REPORT),
            headers={"Content-Type": "text/plain;charset=UTF-8"},
        )

    assert response.status_code == 204
    assert response.headers["access-control-allow-origin"] == "*"
    assert "kind=script_error phase=poll" in caplog.text
    assert "error_name=TypeError line=412 column=17" in caplog.text


def test_a_preflight_is_answered_for_any_site() -> None:
    response = build_client().options(
        ERRORS_PATH,
        headers={
            "Origin": "https://shop.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 204
    assert response.headers["access-control-allow-origin"] == "*"


@pytest.mark.parametrize(
    "report",
    [
        {**REPORT, "message": "Cannot read 'Anna, +995 599 12 34 56'"},
        {**REPORT, "kind": "anything"},
        {**REPORT, "error_name": "Type Error: with text"},
        {**REPORT, "line": -1},
        {"phase": "poll"},
    ],
)
def test_reports_with_texts_or_unknown_values_are_refused(
    report: dict[str, object],
) -> None:
    assert send(build_client(), report) == 422


def test_one_network_cannot_flood_the_reports() -> None:
    client = build_client()

    statuses = [send(client, REPORT) for _ in range(PER_ADDRESS_PER_MINUTE + 1)]

    assert statuses[:-1] == [204] * PER_ADDRESS_PER_MINUTE
    assert statuses[-1] == 429
