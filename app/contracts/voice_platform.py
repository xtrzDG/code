"""Voice platform seam (ElevenLabs Agents in the concept)."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.dto.voice import VoiceAgentSpec
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName


class VoiceAgentProvisionerAdapterContract(AdapterContract, Protocol):
    def list_missing_settings(self) -> list[EnvironmentVariableName]:
        """
        Server settings the voice platform still needs before agents can be
        set up (empty when it is fully configured).
        """
        raise NotImplementedError

    def upsert_agent(self, spec: VoiceAgentSpec) -> VoiceAgentId:
        """
        Create the business's voice agent, or update it when
        `spec.existing_agent_id` is set. Raises ExternalServiceError.
        """
        raise NotImplementedError

    def remove_agent(self, agent_id: VoiceAgentId) -> None:
        """
        Delete the agent and its tools so it answers no more calls; a missing
        agent is not an error. Raises ExternalServiceError.
        """
        raise NotImplementedError
