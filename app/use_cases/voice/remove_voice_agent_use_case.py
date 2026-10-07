import logging

from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.contracts.voice_platform import VoiceAgentProvisionerAdapterContract
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.businesses.prefixed_id import BusinessId

logger: logging.Logger = logging.getLogger(__name__)


class RemoveVoiceAgentUseCase(UseCaseContract[BusinessId, None]):
    """
    Switch the business's voice agent off at the voice platform: when the
    business is paused, moves to a plan without voice, publishes a version
    without voice or disconnects its phone number (concept section 7: the
    agent exists only while voice is part of the live service). Every agent
    id the business's versions know is removed; publishing a voice version
    later creates a new agent.

    Best effort: when the platform cannot be reached the switch is logged
    and the calls are still refused by the call-initiation and tool
    webhooks, which check the same conditions.
    """

    def __init__(
        self,
        assistant_version_repo: AssistantVersionRepoContract,
        voice_agent_provisioner: VoiceAgentProvisionerAdapterContract,
    ) -> None:
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._voice_agent_provisioner: VoiceAgentProvisionerAdapterContract = (
            voice_agent_provisioner
        )

    def run(self, input_data: BusinessId) -> None:
        agent_ids: list[VoiceAgentId] = list(
            dict.fromkeys(
                version.voice_agent_id
                for version in self._assistant_version_repo.list_by_business(input_data)
                if version.voice_agent_id is not None
            )
        )
        for agent_id in agent_ids:
            try:
                self._voice_agent_provisioner.remove_agent(agent_id)
            except ApplicationError as error:
                logger.warning(
                    "Voice agent %s of business %s was not removed: %s",
                    agent_id,
                    input_data,
                    error,
                )
