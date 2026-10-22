"""Voice platform seam (ElevenLabs Agents in the concept)."""

from contextlib import AbstractContextManager
from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.contracts.registry_contract import RegistryContract
from app.schemas.dto.voice import VoiceAgentSpec
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds


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


class VoiceAgentLockRegistryContract(RegistryContract, Protocol):
    def lock_agent(
        self, business_id: BusinessId, wait: LockWaitSeconds
    ) -> AbstractContextManager[object]:
        """
        Held while one process sets up a business's voice agent and records
        what it set up (publishing, rollback, the agents' re-sync), across
        every process: two setups never interleave, so the agent always
        answers with the version that is live. The block calls the voice
        platform and commits its writes as it goes.

        Raises:
            ExternalServiceError: the lock was not free within `wait`.
        """
        raise NotImplementedError
