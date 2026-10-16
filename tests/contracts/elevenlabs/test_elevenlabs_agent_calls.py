"""
What the platform tells ElevenLabs and what the agent sends back: the
agent and tool configurations match the SDK's types with every object
closed, and a tool call or a call start that ElevenLabs makes with the
headers the platform configured is accepted, its answer matching the
SDK's type too.
"""

from typing import Any

import pytest

from app.utilities.channels.channel_endpoints import VOICE_CALL_INITIATION_PATH
from app.utilities.channels.webhook_signatures import sign_body
from tests.channels.channels_payloads import HttpResponse
from tests.channels.recording_transport import RecordedRequest
from tests.channels.voice_agent_specs import build_spec, provisioner
from tests.channels.voice_setup import VoiceSetup, build_voice_setup, tool_secret
from tests.contracts.contract_files import load_json_fixture, read_fixture_bytes
from tests.contracts.elevenlabs.elevenlabs_cases import AGENTS_SPEC, WEBHOOKS_SPEC
from tests.contracts.vendor_schemas import (
    assert_inbound,
    assert_outbound,
    schema_validator,
)

BASE_URL: str = "https://api.workshop.test"
TRANSFER_NUMBER: str = "+995322000001"


def provisioned_setup(existing_agent_id: str | None = None) -> VoiceSetup:
    """A business whose voice agent was created (or updated) at ElevenLabs."""

    setup = build_voice_setup()
    transport = setup.testbed.elevenlabs_transport
    created_agent: dict[str, Any] = load_json_fixture(
        "elevenlabs", "create_agent_response.json"
    )
    transport.respond("POST", r"^/v1/convai/agents/create$", created_agent)
    transport.respond("POST", r"^/v1/convai/tools$", {"id": "tool_0000contract"})
    transport.respond("GET", r"^/v1/convai/agents/", {"agent_id": existing_agent_id})
    transport.respond("PATCH", r"^/v1/convai/agents/", created_agent)
    spec = build_spec(existing_agent_id).model_copy(
        update={
            "business_id": setup.business.id,
            "transfer_phone_number": TRANSFER_NUMBER,
        }
    )
    provisioner(setup.testbed).upsert_agent(spec)
    return setup


def sent(setup: VoiceSetup, method: str, path_end: str) -> list[RecordedRequest]:
    return [
        request
        for request in setup.testbed.elevenlabs_transport.requests
        if request.method == method and request.path.endswith(path_end)
    ]


@pytest.mark.parametrize(
    ("existing_agent_id", "method", "path_end", "root"),
    [
        (None, "POST", "/agents/create", "request:agents.create"),
        (
            "agent_7101k6contract0000",
            "PATCH",
            "/agents/agent_7101k6contract0000",
            "request:agents.update",
        ),
    ],
)
def test_agent_and_tool_configs_match_the_sdk_types(
    existing_agent_id: str | None, method: str, path_end: str, root: str
) -> None:
    setup = provisioned_setup(existing_agent_id)

    [agent] = sent(setup, method, path_end)
    tools = sent(setup, "POST", "/convai/tools")
    assert_outbound(agent.json(), AGENTS_SPEC, root)
    assert len(tools) == 2
    for tool in tools:
        assert_outbound(tool.json(), AGENTS_SPEC, "request:tools.create")


def test_answers_match_the_sdk_types() -> None:
    created: dict[str, Any] = load_json_fixture(
        "elevenlabs", "create_agent_response.json"
    )

    assert_inbound(created, AGENTS_SPEC, "response:agents.create")


def configured_tool(setup: VoiceSetup, tool_name: str) -> dict[str, Any]:
    for request in sent(setup, "POST", "/convai/tools"):
        tool_config: dict[str, Any] = request.json()["tool_config"]
        if tool_config["name"] == tool_name:
            return tool_config

    raise AssertionError(f"No {tool_name} tool was configured.")


def call_configured_tool(
    setup: VoiceSetup, body: bytes, headers: dict[str, str]
) -> HttpResponse:
    api_schema: dict[str, Any] = configured_tool(setup, "create_booking")["api_schema"]
    url: str = api_schema["url"]
    assert url.startswith(BASE_URL)
    return setup.testbed.build_http_client().post(
        url.removeprefix(BASE_URL), content=body, headers=headers
    )


def test_tool_call_matches_the_configured_body_schema() -> None:
    setup = provisioned_setup()
    request_body_schema: dict[str, Any] = configured_tool(setup, "create_booking")[
        "api_schema"
    ]["request_body_schema"]

    # ElevenLabs fills the body from this schema; its own keywords
    # ("dynamic_variable") are annotations to a validator.
    assert schema_validator(request_body_schema).is_valid(
        load_json_fixture("elevenlabs", "tool_call.json")
    )


def test_tool_call_with_the_configured_headers_is_run() -> None:
    setup = provisioned_setup()
    headers: dict[str, str] = configured_tool(setup, "create_booking")["api_schema"][
        "request_headers"
    ]

    response = call_configured_tool(
        setup, read_fixture_bytes("elevenlabs", "tool_call.json"), headers
    )

    assert response.status_code == 200, response.text
    [request] = setup.testbed.voice_tool_orchestrator.requests
    assert request.business_id == setup.business.id
    assert request.provider_call_id == "conv_8401k6contract0001"
    assert request.caller_phone_number == "+995599123456"
    assert request.language == "ka"


def test_tool_call_signed_with_the_body_hmac_is_run() -> None:
    setup = provisioned_setup()
    body: bytes = read_fixture_bytes("elevenlabs", "tool_call.json")

    response = call_configured_tool(
        setup,
        body,
        {
            "X-Assistant-Business-Id": str(setup.business.id),
            "X-Assistant-Signature": "sha256="
            + sign_body(tool_secret(setup.business.id), body),
        },
    )

    assert response.status_code == 200, response.text
    assert len(setup.testbed.voice_tool_orchestrator.requests) == 1


def test_call_start_with_the_configured_headers_is_answered() -> None:
    setup = provisioned_setup()
    [agent] = sent(setup, "POST", "/agents/create")
    webhook: dict[str, Any] = agent.json()["platform_settings"]["workspace_overrides"][
        "conversation_initiation_client_data_webhook"
    ]
    request_body: dict[str, Any] = load_json_fixture(
        "elevenlabs", "conversation_initiation_request.json"
    )
    assert_inbound(request_body, WEBHOOKS_SPEC, "ConversationInitiationRequest")
    assert webhook["url"] == BASE_URL + VOICE_CALL_INITIATION_PATH

    response = setup.testbed.build_http_client().post(
        VOICE_CALL_INITIATION_PATH,
        content=read_fixture_bytes(
            "elevenlabs", "conversation_initiation_request.json"
        ),
        headers=webhook["request_headers"],
    )

    assert response.status_code == 200, response.text
    assert_outbound(response.json(), AGENTS_SPEC, "ConversationInitiationClientData")
