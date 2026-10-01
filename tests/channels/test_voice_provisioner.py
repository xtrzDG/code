import json
from typing import Any

import pytest

from app.adapters.voice.elevenlabs_recording_storage_adapter import (
    ElevenLabsRecordingStorageAdapter,
)
from app.adapters.voice.elevenlabs_voice_agent_provisioner import (
    ElevenLabsVoiceAgentProvisioner,
)
from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.conversations import LlmToolDefinition
from app.schemas.dto.voice import VoiceAgentSpec, VoiceGreeting
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.strings import (
    LlmToolDescription,
    LlmToolInputSchemaJson,
    SystemPromptText,
    VoiceAgentId,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.strings import (
    MessageText,
    RecordingStoragePath,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.webhook_signatures import derive_voice_tool_secret
from tests.channels.testbed import (
    ELEVENLABS_WEBHOOK_SECRET,
    ChannelsTestbed,
    build_settings,
)

BUSINESS_ID = BusinessId()
TOOL_SECRET: str = str(
    derive_voice_tool_secret(PlatformSecret(ELEVENLABS_WEBHOOK_SECRET), BUSINESS_ID)
)
BOOKING_SCHEMA: str = json.dumps(
    {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"type": "string", "description": "Guest name"},
            "starts_at": {"type": "string", "format": "date-time"},
            "party_size": {"type": "integer", "minimum": 1},
        },
        "required": ["name", "starts_at", "party_size"],
    }
)


def tool(name: AssistantToolName, schema: str = BOOKING_SCHEMA) -> LlmToolDefinition:
    return LlmToolDefinition(
        name=name,
        description=LlmToolDescription(f"Use {name.value}."),
        input_schema_json=LlmToolInputSchemaJson(schema),
    )


def build_spec(
    existing_agent_id: str | None = None,
    tools: list[LlmToolDefinition] | None = None,
    languages: tuple[str, ...] = ("ka", "ru", "en"),
) -> VoiceAgentSpec:
    return VoiceAgentSpec(
        business_id=BUSINESS_ID,
        existing_agent_id=None
        if existing_agent_id is None
        else VoiceAgentId(existing_agent_id),
        business_name=BusinessName("Funicular VR"),
        languages=[LanguageTag(tag) for tag in languages],
        default_language=LanguageTag(languages[0]),
        prompt_text=SystemPromptText("You are the AI assistant of Funicular VR."),
        greetings=[
            VoiceGreeting(
                language=LanguageTag(tag), text=MessageText(f"Greeting {tag}")
            )
            for tag in languages
        ],
        tools=tools
        if tools is not None
        else [
            tool(AssistantToolName.CREATE_BOOKING),
            tool(AssistantToolName.SEARCH_KNOWLEDGE, '{"type": "object"}'),
        ],
        tool_webhook_base_url=PublicBaseUrl("https://api.workshop.test/"),
    )


def provisioner(testbed: ChannelsTestbed) -> ElevenLabsVoiceAgentProvisioner:
    return ElevenLabsVoiceAgentProvisioner(testbed.elevenlabs_client, testbed.settings)


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
                    "agent": {"first_message": "Greeting ru", "language": "ru"}
                }
            },
            "en": {
                "overrides": {
                    "agent": {"first_message": "Greeting en", "language": "en"}
                }
            },
        }
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
        assert destination["transfer_destination"] == {
            "type": "phone",
            "phone_number": "+995599000111",
        }
        assert "{{is_open_now}}" in destination["condition"]
        assert "handoff_to_human" in destination["condition"]
        assert agent_config["dynamic_variables"] == {
            "dynamic_variable_placeholders": {"is_open_now": "no"}
        }

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


class TestAgentUpdate:
    def test_tools_are_updated_by_name_and_stale_ones_deleted_afterwards(self) -> None:
        testbed = ChannelsTestbed()
        transport = testbed.elevenlabs_transport
        transport.respond(
            "GET",
            r"^/v1/convai/agents/agent_1$",
            {
                "agent_id": "agent_1",
                "conversation_config": {
                    "agent": {
                        "prompt": {"tool_ids": ["t_booking", "t_price", "t_other"]}
                    }
                },
            },
        )
        transport.respond(
            "GET",
            r"/tools/t_booking$",
            {"id": "t_booking", "tool_config": {"name": "create_booking"}},
        )
        transport.respond(
            "GET",
            r"/tools/t_price$",
            {"id": "t_price", "tool_config": {"name": "get_price"}},
        )
        transport.respond(
            "GET",
            r"/tools/t_other$",
            {"id": "t_other", "tool_config": {"name": "weather"}},
        )
        transport.respond("PATCH", r"/tools/", {"id": "x"})
        transport.respond("POST", r"^/v1/convai/tools$", {"id": "t_search"})
        transport.respond(
            "PATCH", r"^/v1/convai/agents/agent_1$", {"agent_id": "agent_1"}
        )
        transport.respond("DELETE", r"/tools/", {})

        agent_id = provisioner(testbed).upsert_agent(build_spec("agent_1"))

        assert agent_id == "agent_1"
        sequence = [(r.method, r.path) for r in transport.requests if r.method != "GET"]
        assert sequence == [
            ("PATCH", "/v1/convai/tools/t_booking"),
            ("POST", "/v1/convai/tools"),
            ("PATCH", "/v1/convai/agents/agent_1"),
            ("DELETE", "/v1/convai/tools/t_price"),
        ]
        patched = transport.requests_to("/agents/agent_1")[-1].json()
        assert patched["conversation_config"]["agent"]["prompt"]["tool_ids"] == [
            "t_booking",
            "t_search",
        ]

    def test_missing_agent_is_created_again(self) -> None:
        testbed = ChannelsTestbed()
        transport = testbed.elevenlabs_transport
        transport.respond(
            "GET", r"^/v1/convai/agents/agent_gone$", {"detail": "x"}, 404
        )
        transport.respond(
            "POST", r"^/v1/convai/agents/create$", {"agent_id": "agent_2"}
        )

        agent_id = provisioner(testbed).upsert_agent(build_spec("agent_gone", tools=[]))

        assert agent_id == "agent_2"

    def test_removed_agent_and_its_tools_are_deleted(self) -> None:
        testbed = ChannelsTestbed()
        transport = testbed.elevenlabs_transport
        transport.respond(
            "GET",
            r"^/v1/convai/agents/agent_1$",
            {"conversation_config": {"agent": {"prompt": {"tool_ids": ["t_1"]}}}},
        )
        transport.respond("DELETE", r"^/v1/convai/agents/agent_1$", {})
        transport.respond("DELETE", r"^/v1/convai/tools/t_1$", {})

        provisioner(testbed).remove_agent(VoiceAgentId("agent_1"))

        assert [(r.method, r.path) for r in transport.requests] == [
            ("GET", "/v1/convai/agents/agent_1"),
            ("DELETE", "/v1/convai/agents/agent_1"),
            ("DELETE", "/v1/convai/tools/t_1"),
        ]

    def test_removing_an_agent_that_is_gone_is_not_an_error(self) -> None:
        testbed = ChannelsTestbed()
        transport = testbed.elevenlabs_transport
        transport.respond("GET", r"^/v1/convai/agents/agent_gone$", {}, 404)
        transport.respond("DELETE", r"^/v1/convai/agents/agent_gone$", {}, 404)

        provisioner(testbed).remove_agent(VoiceAgentId("agent_gone"))

        assert [r.method for r in transport.requests] == ["GET", "DELETE"]

    def test_stale_tool_deletion_failures_are_tolerated(self) -> None:
        testbed = ChannelsTestbed()
        transport = testbed.elevenlabs_transport
        transport.respond(
            "GET",
            r"^/v1/convai/agents/agent_1$",
            {"conversation_config": {"agent": {"prompt": {"tool_ids": ["t_old"]}}}},
        )
        transport.respond(
            "GET", r"/tools/t_old$", {"tool_config": {"name": "send_link"}}
        )
        transport.respond("PATCH", r"^/v1/convai/agents/agent_1$", {})
        transport.respond("DELETE", r"/tools/t_old$", {"detail": "in use"}, 409)

        assert (
            provisioner(testbed).upsert_agent(build_spec("agent_1", tools=[]))
            == "agent_1"
        )


class TestRecordingStorage:
    def test_platform_recordings_are_deleted_there_others_go_to_the_fallback(
        self,
    ) -> None:
        testbed = ChannelsTestbed()
        testbed.elevenlabs_transport.respond("DELETE", r"/conversations/", {})
        deleted_elsewhere: list[str] = []

        class LocalStorage(RecordingStorageAdapterContract):
            def delete(self, recording_path: RecordingStoragePath) -> None:
                deleted_elsewhere.append(str(recording_path))

        storage = ElevenLabsRecordingStorageAdapter(
            testbed.elevenlabs_client, LocalStorage()
        )
        storage.delete(RecordingStoragePath("elevenlabs/conversations/conv_1"))
        storage.delete(RecordingStoragePath("calls/2026/conv_2.mp3"))

        [request] = testbed.elevenlabs_transport.requests
        assert (request.method, request.path) == (
            "DELETE",
            "/v1/convai/conversations/conv_1",
        )
        assert deleted_elsewhere == ["calls/2026/conv_2.mp3"]

    def test_missing_recordings_are_not_errors(self) -> None:
        testbed = ChannelsTestbed()
        testbed.elevenlabs_transport.respond("DELETE", r"/conversations/", {}, 404)

        ElevenLabsRecordingStorageAdapter(testbed.elevenlabs_client).delete(
            RecordingStoragePath("elevenlabs/conversations/conv_1")
        )
        ElevenLabsRecordingStorageAdapter(testbed.elevenlabs_client).delete(
            RecordingStoragePath("local/file.mp3")
        )

    def test_platform_errors_are_raised(self) -> None:
        testbed = ChannelsTestbed()
        testbed.elevenlabs_transport.respond(
            "DELETE", r"/conversations/", {"detail": "x"}, 500
        )

        with pytest.raises(ExternalServiceError):
            ElevenLabsRecordingStorageAdapter(testbed.elevenlabs_client).delete(
                RecordingStoragePath("elevenlabs/conversations/conv_1")
            )
