"""
On a call the caller id proves nobody's identity: the tools that read or
change a customer's bookings never run from the voice agent, once the
webhook is authenticated, and the agent hears to hand the request to staff.
"""

import pytest

from tests.channels.channels_payloads import HttpResponse, to_json_bytes
from tests.channels.voice_setup import (
    CALLER,
    VoiceSetup,
    build_voice_setup,
    tool_secret,
)


def call_tool(setup: VoiceSetup, tool_name: str, secret: str | None) -> HttpResponse:
    headers: dict[str, str] = {"X-Assistant-Business-Id": str(setup.business.id)}
    if secret is not None:
        headers["X-Assistant-Tool-Secret"] = secret

    return setup.testbed.build_http_client().post(
        f"/v1/voice/tools/{tool_name}",
        content=to_json_bytes(
            {
                "arguments": {"date": "2026-10-03"},
                "conversation_id": "conv_1",
                "caller_id": CALLER,
            }
        ),
        headers=headers,
    )


@pytest.mark.parametrize(
    "tool_name", ["list_my_bookings", "cancel_booking", "reschedule_booking"]
)
def test_identity_bound_tools_are_refused_with_what_to_do(tool_name: str) -> None:
    setup = build_voice_setup()

    response = call_tool(setup, tool_name, tool_secret(setup.business.id))

    assert response.status_code == 200, response.text
    error: str = response.json()["error"]
    assert "does not prove who is calling" in error
    assert "handoff_to_human" in error
    assert setup.testbed.voice_tool_orchestrator.requests == []


@pytest.mark.parametrize("secret", [None, "wrong-secret"])
def test_the_refusal_still_needs_the_business_secret(secret: str | None) -> None:
    setup = build_voice_setup()

    response = call_tool(setup, "cancel_booking", secret)

    assert response.status_code == 401, response.text
    assert "error" not in response.json() or "prove" not in str(response.json())


def test_other_tools_still_run() -> None:
    setup = build_voice_setup()

    response = call_tool(setup, "check_availability", tool_secret(setup.business.id))

    assert response.status_code == 200, response.text
    [request] = setup.testbed.voice_tool_orchestrator.requests
    assert request.tool_name.value == "check_availability"
