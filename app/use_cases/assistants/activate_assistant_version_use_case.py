from typed_time_provider import Microseconds, WallClock

from app.contracts.assistant_assembly import AssistantToolCatalogContract
from app.contracts.repositories import (
    AssistantVersionRepoContract,
    BusinessRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.contracts.voice_platform import VoiceAgentProvisionerAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.assistants import AssistantVersionActivation
from app.schemas.dto.conversations import CallGreeting, CallGreetingRequest
from app.schemas.dto.voice import VoiceAgentSpec, VoiceGreeting
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.utilities.assembly.voice_agents import find_existing_voice_agent_id


class ActivateAssistantVersionUseCase(
    UseCaseContract[AssistantVersionActivation, AssistantVersionDocument]
):
    """
    Make an already authorized and checked version the live one (shared by
    publishing and rollback).

    With voice enabled, the business's voice agent is created or updated
    first from the same version: its instruction, a greeting in every
    language, the chat's tool definitions and the public base URL for the
    tool webhooks. The agent id of earlier versions is reused (one agent
    per business). If that fails, ExternalServiceError is raised and
    nothing is published. Then the previously published version is
    archived, this one is published, and the business goes live with it.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        voice_agent_provisioner: VoiceAgentProvisionerAdapterContract,
        build_call_greeting: UseCaseContract[CallGreetingRequest, CallGreeting],
        assistant_tool_catalog: AssistantToolCatalogContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._voice_agent_provisioner: VoiceAgentProvisionerAdapterContract = (
            voice_agent_provisioner
        )
        self._build_call_greeting: UseCaseContract[
            CallGreetingRequest,
            CallGreeting,
        ] = build_call_greeting
        self._assistant_tool_catalog: AssistantToolCatalogContract = (
            assistant_tool_catalog
        )
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AssistantVersionActivation) -> AssistantVersionDocument:
        business: BusinessDocument = input_data.business
        version: AssistantVersionDocument = input_data.version
        versions: list[AssistantVersionDocument] = (
            self._assistant_version_repo.list_by_business(business.id)
        )
        voice_agent_id: VoiceAgentId | None = version.voice_agent_id
        if version.is_voice_enabled:
            voice_agent_id = self._provision_voice_agent(business, version, versions)

        now: Microseconds = self._wall_clock.now_unix()
        for other_version in versions:
            if (
                other_version.id != version.id
                and other_version.status is AssistantVersionStatus.PUBLISHED
            ):
                other_version.status = AssistantVersionStatus.ARCHIVED
                other_version.updated_at = now
                self._assistant_version_repo.save(other_version)

        version.status = AssistantVersionStatus.PUBLISHED
        version.published_at = now
        version.voice_agent_id = voice_agent_id
        version.updated_at = now
        self._assistant_version_repo.save(version)

        business.published_assistant_version_id = version.id
        business.status = BusinessStatus.LIVE
        business.updated_at = now
        self._business_repo.save(business)
        return version

    def _provision_voice_agent(
        self,
        business: BusinessDocument,
        version: AssistantVersionDocument,
        versions: list[AssistantVersionDocument],
    ) -> VoiceAgentId:
        base_url: PublicBaseUrl | None = self._app_settings.app_base_url
        if base_url is None:
            raise ExternalServiceError(
                "The voice agent cannot be set up: APP_BASE_URL for its tool "
                "webhooks is not configured."
            )

        try:
            spec = VoiceAgentSpec(
                business_id=business.id,
                existing_agent_id=find_existing_voice_agent_id(versions, version),
                business_name=business.name,
                languages=list(version.languages),
                default_language=version.default_language,
                prompt_text=version.prompt_text,
                greetings=self._build_greetings(business, version),
                tools=self._assistant_tool_catalog.list_definitions(version.tools),
                tool_webhook_base_url=base_url,
            )
            return self._voice_agent_provisioner.upsert_agent(spec)
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
