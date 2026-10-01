"""Voice platform seam (ElevenLabs Agents in the concept)."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.dto.voice import VoiceAgentSpec
from app.schemas.typings.assistants.strings import VoiceAgentId


class VoiceAgentProvisionerAdapterContract(AdapterContract, Protocol):
    def upsert_agent(self, spec: VoiceAgentSpec) -> VoiceAgentId:
        """
        Create the business's voice agent, or update it when
        `spec.existing_agent_id` is set. Raises ExternalServiceError.
        """
        raise NotImplementedError
