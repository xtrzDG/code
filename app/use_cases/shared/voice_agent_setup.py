"""Setting up a business's voice agent from one version (publishing, re-sync)."""

from app.contracts.voice_platform import VoiceAgentProvisionerAdapterContract
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.use_cases.shared.voice_agent_specs import (
    VoiceAgentSources,
    build_voice_agent_spec,
)


class VoiceAgentSetup:
    """
    The voice agent of a business, built from one version (concept section
    7: same instruction and tools as the chat; `build_voice_agent_spec`):
    the version's phone instruction, a greeting and a tuned voice in every
    language of the version, the tools with decline_recording behind the
    public base URL of the tool webhooks, the transfer to the profile's
    handoff phone in opening hours, and the speech recognition's keywords.
    An existing agent is updated in place, so its phone number keeps
    working.
    """

    def __init__(
        self,
        sources: VoiceAgentSources,
        voice_agent_provisioner: VoiceAgentProvisionerAdapterContract,
    ) -> None:
        self._sources: VoiceAgentSources = sources
        self._provisioner: VoiceAgentProvisionerAdapterContract = (
            voice_agent_provisioner
        )

    def is_configured(self) -> bool:
        """The voice platform's settings and APP_BASE_URL are all set."""

        return (
            not self._provisioner.list_missing_settings()
            and self._sources.app_settings.app_base_url is not None
        )

    def set_up(
        self,
        business: BusinessDocument,
        version: AssistantVersionDocument,
        existing_agent_id: VoiceAgentId | None,
    ) -> VoiceAgentId:
        """
        Create or update the agent; its id.

        Raises:
            ExternalServiceError: APP_BASE_URL is not set, or the voice
                platform refused or could not be reached.
        """

        base_url: PublicBaseUrl | None = self._sources.app_settings.app_base_url
        if base_url is None:
            raise ExternalServiceError(
                "The voice agent cannot be set up: APP_BASE_URL for its tool "
                "webhooks is not configured."
            )

        try:
            return self._provisioner.upsert_agent(
                build_voice_agent_spec(
                    self._sources, business, version, existing_agent_id, base_url
                )
            )
        except ExternalServiceError:
            raise
        except ApplicationError as error:
            raise ExternalServiceError(
                f"The voice agent could not be set up: {error}"
            ) from error
