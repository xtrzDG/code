"""Creating the ElevenLabs voice agent of a business."""

import json
from typing import Any

import pytest

from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.utilities.channels.voice_service import (
    MAX_CONCURRENT_CALLS,
    MAX_DAILY_CALLS,
)
from tests.channels.channels_settings import build_settings
from tests.channels.testbed import ChannelsTestbed
from tests.channels.voice_agent_specs import (
    BUSINESS_ID,
    TOOL_SECRET,
    build_spec,
    provisioner,
    voice_of,
)


class TestAgentCreation:
    def test_new_agent_with_webhook_tools(self) -> None:
        testbed = ChannelsTestbed()
        transport = testbed.elevenlabs_transport
        transport.respond("POST", r"^/v1/convai/tools$", {"id": "tool_new"})
        transport.respond(
            "POST", r"^/v1/convai/agents/create$", {"agent_id": "agent_1"}
        )

        agent_id = provisioner(testbed).upsert_agent(build_spec())

        assert agent_id == "agent_1"
        tool_requests = transport.requests_to("/v1/convai/tools")
        assert len(tool_requests) == 2
        assert all(
            r.headers["xi-api-key"] == "elevenlabs-api-key" for r in transport.requests
        )
        booking_tool: dict[str, Any] = tool_requests[0].json()["tool_config"]
        assert booking_tool["type"] == "webhook"
        assert booking_tool["name"] == "create_booking"
        api_schema = booking_tool["api_schema"]
        assert (
            api_schema["url"]
            == "https://api.workshop.test/v1/voice/tools/create_booking"
        )
        assert api_schema["method"] == "POST"
        assert api_schema["request_headers"] == {
            "X-Assistant-Business-Id": str(BUSINESS_ID),
            "X-Assistant-Tool-Secret": TOOL_SECRET,
        }
        body_schema = api_schema["request_body_schema"]
        assert body_schema["required"] == ["arguments", "conversation_id"]
        assert body_schema["properties"]["conversation_id"] == {
            "type": "string",
            "dynamic_variable": "system__conversation_id",
        }
        assert body_schema["properties"]["caller_id"]["dynamic_variable"] == (
            "system__caller_id"
        )
        arguments = body_schema["properties"]["arguments"]
        assert arguments["required"] == ["name", "starts_at", "party_size"]
        assert arguments["properties"]["party_size"] == {
            "type": "integer",
            "description": "party size",
        }
        assert "additionalProperties" not in json.dumps(arguments)

        agent: dict[str, Any] = transport.requests_to("/agents/create")[0].json()
        assert agent["tags"] == ["assistant-workshop", str(BUSINESS_ID)]
        config = agent["conversation_config"]
        assert config["agent"]["first_message"] == "Greeting ka"
        assert config["agent"]["language"] == "ka"
        assert config["agent"]["prompt"]["tool_ids"] == ["tool_new", "tool_new"]
        assert set(config["agent"]["prompt"]["built_in_tools"]) == {
            "end_call",
            "language_detection",
        }
        assert config["language_presets"] == {
            "ru": {
                "overrides": {
                    "agent": {"first_message": "Greeting ru", "language": "ru"},
                    "tts": voice_of("ru"),
                }
            },
            "en": {
                "overrides": {
                    "agent": {"first_message": "Greeting en", "language": "en"},
                    "tts": voice_of("en"),
                }
            },
        }
        # The default language's voice is the agent's own.
        assert config["tts"] == voice_of("ka")
        platform = agent["platform_settings"]
        assert platform["overrides"][
            "enable_conversation_initiation_client_data_from_webhook"
        ]
        webhook = platform["workspace_overrides"][
            "conversation_initiation_client_data_webhook"
        ]
        assert webhook["url"] == (
            "https://api.workshop.test/v1/voice/webhooks/conversation-initiation"
        )
        assert webhook["request_headers"]["X-Assistant-Tool-Secret"] == TOOL_SECRET

    def test_single_language_agent_has_no_presets(self) -> None:
        testbed = ChannelsTestbed()
        testbed.elevenlabs_transport.respond(
            "POST", r"^/v1/convai/agents/create$", {"agent_id": "agent_pl"}
        )

        provisioner(testbed).upsert_agent(build_spec(tools=[], languages=("pl",)))

        agent = testbed.elevenlabs_transport.requests_to("/agents/create")[0].json()
        assert "language_presets" not in agent["conversation_config"]
        assert set(
            agent["conversation_config"]["agent"]["prompt"]["built_in_tools"]
        ) == {"end_call"}

    def test_staff_transfer_is_offered_only_with_a_number_and_when_open(
        self,
    ) -> None:
        testbed = ChannelsTestbed()
        testbed.elevenlabs_transport.respond(
            "POST", r"^/v1/convai/agents/create$", {"agent_id": "agent_tr"}
        )
        spec = build_spec(tools=[]).model_copy(
            update={"transfer_phone_number": E164PhoneNumber("+995599000111")}
        )

        provisioner(testbed).upsert_agent(spec)

        agent = testbed.elevenlabs_transport.requests_to("/agents/create")[0].json()
        agent_config = agent["conversation_config"]["agent"]
        transfer = agent_config["prompt"]["built_in_tools"]["transfer_to_number"]
        assert transfer["params"]["system_tool_type"] == "transfer_to_number"
        [destination] = transfer["params"]["transfers"]
        # Never a number fixed in the agent: the call's transfer_number,
        # which the call-initiation webhook sets only while open.
        assert destination["transfer_destination"] == {
            "type": "phone_dynamic_variable",
            "phone_number": "transfer_number",
        }
        assert "+995599000111" not in json.dumps(agent)
        assert "{{is_open_now}}" in destination["condition"]
        assert "{{transfer_number}}" in destination["condition"]
        assert "handoff_to_human" in destination["condition"]
        assert agent_config["dynamic_variables"] == {
            "dynamic_variable_placeholders": {
                "is_open_now": "no",
                "transfer_number": "none",
                "local_now": "unknown",
                "next_days": "unknown",
                "timezone": "unknown",
            }
        }

    def test_the_agent_starts_no_conversation_without_a_signed_url(self) -> None:
        testbed = ChannelsTestbed()
        testbed.elevenlabs_transport.respond(
            "POST", r"^/v1/convai/agents/create$", {"agent_id": "agent_auth"}
        )

        provisioner(testbed).upsert_agent(build_spec(tools=[]))

        agent = testbed.elevenlabs_transport.requests_to("/agents/create")[0].json()
        platform = agent["platform_settings"]
        assert platform["auth"] == {
            "enable_auth": True,
            "allowlist": [],
            "require_origin_header": True,
        }
        assert platform["call_limits"] == {
            "agent_concurrency_limit": MAX_CONCURRENT_CALLS,
            "daily_limit": MAX_DAILY_CALLS,
            "bursting_enabled": False,
        }
        # Phone calls still start through the call-initiation webhook.
        assert platform["overrides"][
            "enable_conversation_initiation_client_data_from_webhook"
        ]

    def test_brazilian_portuguese_uses_the_regional_code(self) -> None:
        testbed = ChannelsTestbed()
        testbed.elevenlabs_transport.respond(
            "POST", r"^/v1/convai/agents/create$", {"agent_id": "agent_br"}
        )

        provisioner(testbed).upsert_agent(
            build_spec(tools=[], languages=("pt-BR", "en"))
        )

        agent = testbed.elevenlabs_transport.requests_to("/agents/create")[0].json()
        assert agent["conversation_config"]["agent"]["language"] == "pt-br"

    def test_failed_agent_creation_removes_the_new_tools(self) -> None:
        testbed = ChannelsTestbed()
        transport = testbed.elevenlabs_transport
        transport.respond("POST", r"^/v1/convai/tools$", {"id": "tool_new"})
        transport.respond(
            "POST",
            r"^/v1/convai/agents/create$",
            {"detail": {"message": "language not supported"}},
            status_code=422,
        )
        transport.respond("DELETE", r"^/v1/convai/tools/", {})

        with pytest.raises(ExternalServiceError, match="language not supported"):
            provisioner(testbed).upsert_agent(build_spec())

        assert len([r for r in transport.requests if r.method == "DELETE"]) == 2

    def test_webhook_secret_is_required(self) -> None:
        testbed = ChannelsTestbed(build_settings(ELEVENLABS_WEBHOOK_SECRET=""))

        with pytest.raises(ExternalServiceError, match="ELEVENLABS_WEBHOOK_SECRET"):
            provisioner(testbed).upsert_agent(build_spec())

        assert testbed.elevenlabs_transport.requests == []
