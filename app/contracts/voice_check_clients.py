"""
ElevenLabs agent testing: simulated calls against an agent (the voice
checks of autotests), and the client of every ElevenLabs API together.
"""

from typing import Protocol

from app.contracts.channel_clients import ElevenLabsApiClientContract, JsonObject
from app.contracts.client_contract import ClientContract
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.voice.constrained_strings import (
    VoiceCheckInvocationId,
    VoiceCheckTestId,
)


class ElevenLabsAgentTestingClientContract(ClientContract, Protocol):
    """
    ElevenLabs agent testing: POST /v1/convai/agent-testing/create, POST
    /v1/convai/agents/{agent_id}/run-tests, GET
    /v1/convai/test-invocations/{id} and DELETE
    /v1/convai/agent-testing/{test_id}. Every method raises
    ExternalServiceError when the platform refuses or cannot be reached.
    """

    def create_test(self, test_config: JsonObject) -> VoiceCheckTestId:
        """Create one test (a simulated call); its id."""
        raise NotImplementedError

    def run_tests(
        self,
        agent_id: VoiceAgentId,
        test_ids: list[VoiceCheckTestId],
        agent_config_override: JsonObject | None,
    ) -> VoiceCheckInvocationId:
        """
        Start the tests against the agent, with `agent_config_override` (a
        whole `conversation_config` and `platform_settings`) instead of the
        agent's own configuration when given; the run's id, polled with
        `get_test_invocation`.
        """
        raise NotImplementedError

    def get_test_invocation(
        self, invocation_id: VoiceCheckInvocationId
    ) -> JsonObject | None:
        """The run with its tests' results so far; None when it is gone."""
        raise NotImplementedError

    def delete_test(self, test_id: VoiceCheckTestId) -> None:
        """Delete a test; a missing one is not an error."""
        raise NotImplementedError


class ElevenLabsPlatformClientContract(
    ElevenLabsApiClientContract, ElevenLabsAgentTestingClientContract, Protocol
):
    """Every ElevenLabs API the platform calls, through one client."""
