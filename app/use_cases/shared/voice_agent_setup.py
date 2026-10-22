"""Setting up a business's voice agent from one version (publishing, re-sync)."""

from app.contracts.assistant_assembly import AssistantToolCatalogContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.contracts.voice_platform import VoiceAgentProvisionerAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.conversations import CallGreeting, CallGreetingRequest
from app.schemas.dto.voice import VoiceAgentSpec, VoiceGreeting
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.utilities.channels.voice_service import find_transfer_phone_number
from app.utilities.conversations.tool_selection import select_voice_agent_tools


class VoiceAgentSetup:
    """
    The voice agent of a business, built from one version (concept section
    7: same instruction and tools as the chat): the version's phone
    instruction (its chat instruction for a version assembled before it),
    a greeting in every language of the version, the tools of
    `select_voice_agent_tools` (with decline_recording) behind the public
    base URL of the tool webhooks, and in opening hours a transfer to the
    profile's handoff phone (or a manager reachable by phone). An existing
    agent is updated in place, so its phone number keeps working.
    """

    def __init__(
        self,
        business_profile_repo: BusinessProfileRepoContract,
        voice_agent_provisioner: VoiceAgentProvisionerAdapterContract,
        build_call_greeting: UseCaseContract[CallGreetingRequest, CallGreeting],
        assistant_tool_catalog: AssistantToolCatalogContract,
        app_settings: AppSettings,
    ) -> None:
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._provisioner: VoiceAgentProvisionerAdapterContract = (
            voice_agent_provisioner
        )
        self._build_call_greeting: UseCaseContract[
            CallGreetingRequest, CallGreeting
        ] = build_call_greeting
        self._assistant_tool_catalog: AssistantToolCatalogContract = (
            assistant_tool_catalog
        )
        self._app_settings: AppSettings = app_settings

    def is_configured(self) -> bool:
        """The voice platform's settings and APP_BASE_URL are all set."""

        return (
            not self._provisioner.list_missing_settings()
            and self._app_settings.app_base_url is not None
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

        base_url: PublicBaseUrl | None = self._app_settings.app_base_url
        if base_url is None:
            raise ExternalServiceError(
                "The voice agent cannot be set up: APP_BASE_URL for its tool "
                "webhooks is not configured."
            )

        try:
            spec = VoiceAgentSpec(
                business_id=business.id,
                existing_agent_id=existing_agent_id,
                business_name=business.name,
                languages=list(version.languages),
                default_language=version.default_language,
                prompt_text=version.phone_prompt_text or version.prompt_text,
                greetings=self._build_greetings(business, version),
                tools=self._assistant_tool_catalog.list_definitions(
                    select_voice_agent_tools(version)
                ),
                tool_webhook_base_url=base_url,
                transfer_phone_number=find_transfer_phone_number(
                    business,
                    self._business_profile_repo.get_by_business(business.id),
                ),
            )
            return self._provisioner.upsert_agent(spec)
        except ExternalServiceError:
            raise
        except ApplicationError as error:
            raise ExternalServiceError(
                f"The voice agent could not be set up: {error}"
            ) from error

    def _build_greetings(
        self,
        business: BusinessDocument,
        version: AssistantVersionDocument,
    ) -> list[VoiceGreeting]:
        greetings: list[VoiceGreeting] = []
        for language in version.languages:
            greeting: CallGreeting = self._build_call_greeting.run(
                CallGreetingRequest(business_id=business.id, language=language)
            )
            if any(existing.language == greeting.language for existing in greetings):
                continue

            greetings.append(
                VoiceGreeting(language=greeting.language, text=greeting.text)
            )

        return greetings
