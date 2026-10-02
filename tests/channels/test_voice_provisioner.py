"""Updating the ElevenLabs voice agent and reading call recordings."""

import pytest

from app.adapters.voice.elevenlabs_recording_storage_adapter import (
    ElevenLabsRecordingStorageAdapter,
)
from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.schemas.dto.call_recordings import RecordingAudio
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.conversations.strings import RecordingStoragePath
from tests.channels.testbed import ChannelsTestbed
from tests.channels.voice_agent_specs import build_spec, provisioner


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
            def read(
                self, recording_path: RecordingStoragePath
            ) -> RecordingAudio | None:
                raise AssertionError("Deleting reads nothing.")

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
