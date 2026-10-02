import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.assistant_assembly import AssistantToolCatalogContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.contracts.voice_platform import VoiceAgentProvisionerAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import AssistantVersionStatus, GoLiveCheckCode
from app.schemas.constants.businesses import BusinessStatus, ServiceMode
from app.schemas.constants.setup import ActivationEventKind
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.assistants.assembly_sources import AssistantVersionActivation
from app.schemas.dto.billing_go_live import GoLiveTrial, GoLiveTrialRequest
from app.schemas.dto.conversations import CallGreeting, CallGreetingRequest
from app.schemas.dto.go_live import (
    GoLiveCheck,
    GoLiveReadiness,
    GoLiveReadinessRequest,
)
from app.schemas.dto.setup.setup_progress import ActivationEventRecord
from app.schemas.dto.voice import VoiceAgentSpec, VoiceGreeting
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ExternalServiceError,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.utilities.assembly.go_live_refusals import (
    build_check_reason,
    describe_go_live_refusal,
    find_blocking_failures,
    is_voice_configured,
)
from app.utilities.assembly.voice_agents import find_existing_voice_agent_id
from app.utilities.businesses.business_revisions import build_stale_revision_error
from app.utilities.channels.voice_service import find_transfer_phone_number

LOGGER: logging.Logger = logging.getLogger(__name__)
# Whether an untested version may go live is decided by publishing (a
# platform admin may force it); rollback restores a version that was live.
CHECKS_DECIDED_BY_CALLER: frozenset[GoLiveCheckCode] = frozenset(
    {GoLiveCheckCode.AUTOTESTS}
)


class ActivateAssistantVersionUseCase(
    UseCaseContract[AssistantVersionActivation, AssistantVersionDocument]
):
    """
    Make an already authorized and checked version the live one (shared by
    publishing and rollback).

    First every launch condition of the go-live checklist is checked (trial
    or subscription, the data processing agreement, nothing blocking in the
    profile, a staff contact, voice settings in production); a missing one
    is a ConflictError whose reasons carry the check codes, and nothing
    changes. The autotests are the caller's decision. With voice enabled, the
    business's voice agent is created or updated first from the same
    version: its phone instruction, a greeting in every language, the chat's tool
    definitions and the public base URL for the tool webhooks. The agent id
    of earlier versions is reused (one agent per business). In opening
    hours a caller may be put through to the profile's handoff phone (or a
    manager reachable by phone). The agent gets the version's phone
    instruction (spoken facts, no links). If that fails,
    ExternalServiceError is raised and nothing is published. Then the
    business goes live with this version (see `_store_business`: a save
    made meanwhile is never overwritten), the previously published version
    is archived and this one is published. Activating a version without voice
    removes the agent of earlier versions. In development and test, a voice
    version goes live without an agent while ElevenLabs is not configured
    (a warning is logged). The first go-live starts the free trial when it
    is still due (the business takes its plan with full service in the same
    write) and is recorded as the WENT_LIVE milestone.
    """

    def __init__(
        self,
        check_go_live_readiness: UseCaseContract[
            GoLiveReadinessRequest, GoLiveReadiness
        ],
        remove_voice_agent: UseCaseContract[BusinessId, None],
        business_profile_repo: BusinessProfileRepoContract,
        business_repo: BusinessRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        voice_agent_provisioner: VoiceAgentProvisionerAdapterContract,
        build_call_greeting: UseCaseContract[CallGreetingRequest, CallGreeting],
        assistant_tool_catalog: AssistantToolCatalogContract,
        start_trial_at_go_live: UseCaseContract[GoLiveTrialRequest, GoLiveTrial],
        record_activation_event: UseCaseContract[ActivationEventRecord, None],
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._check_go_live_readiness: UseCaseContract[
            GoLiveReadinessRequest, GoLiveReadiness
        ] = check_go_live_readiness
        self._remove_voice_agent: UseCaseContract[BusinessId, None] = remove_voice_agent
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
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
        self._start_trial_at_go_live: UseCaseContract[
            GoLiveTrialRequest, GoLiveTrial
        ] = start_trial_at_go_live
        self._record_activation_event: UseCaseContract[ActivationEventRecord, None] = (
            record_activation_event
        )
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AssistantVersionActivation) -> AssistantVersionDocument:
        business: BusinessDocument = input_data.business
        version: AssistantVersionDocument = input_data.version
        readiness: GoLiveReadiness = self._check_go_live_readiness.run(
            GoLiveReadinessRequest(business=business, version=version)
        )
        failures: list[GoLiveCheck] = find_blocking_failures(
            readiness, CHECKS_DECIDED_BY_CALLER
        )
        if failures:
            raise ConflictError(
                describe_go_live_refusal(failures),
                reasons=[build_check_reason(check) for check in failures],
            )

        versions: list[AssistantVersionDocument] = (
            self._assistant_version_repo.list_by_business(business.id)
        )
        voice_agent_id: VoiceAgentId | None = version.voice_agent_id
        if version.is_voice_enabled and is_voice_configured(readiness):
            voice_agent_id = self._provision_voice_agent(business, version, versions)
        elif version.is_voice_enabled:
            LOGGER.warning(
                "Version %s of business %s goes live without a voice agent: "
                "the voice platform is not configured on this server.",
                version.id,
                business.id,
            )
        elif any(other.voice_agent_id is not None for other in versions):
            # A version without voice: the agent of an earlier version must
            # not keep answering calls with the old instruction.
            self._remove_voice_agent.run(business.id)

        trial: GoLiveTrial = self._start_trial_at_go_live.run(
            GoLiveTrialRequest(business=business)
        )
        now: Microseconds = self._wall_clock.now_unix()
        # The business first: when that write is refused, the versions stay
        # as they were and the business keeps pointing at its live one.
        self._store_business(input_data, trial, now)
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
        self._record_activation_event.run(
            ActivationEventRecord(
                business_id=business.id,
                kind=ActivationEventKind.WENT_LIVE,
                occurred_at=now,
            )
        )
        return version

    def _store_business(
        self,
        activation: AssistantVersionActivation,
        trial: GoLiveTrial,
        now: Microseconds,
    ) -> None:
        """
        Point the business at the version and make it live. Setting up the
        voice agent takes seconds, so the business is never written from the
        copy read before it: activation's fields go onto the business as
        stored now, or, when the caller changed the business too, the whole
        copy is written only while nobody saved the business since it was
        read (else nothing is written and the change is refused as stale).
        """

        business: BusinessDocument = activation.business
        version_id: AssistantVersionId = activation.version.id

        def go_live(target: BusinessDocument) -> None:
            target.published_assistant_version_id = version_id
            target.status = BusinessStatus.LIVE
            if trial.plan_key is not None:
                # The trial started now: its plan, served in full.
                target.plan_key = trial.plan_key
                target.service_mode = ServiceMode.FULL

            target.updated_at = now

        if activation.carries_business_changes:
            go_live(business)
            if not self._business_repo.save_if_unchanged(business):
                raise build_stale_revision_error(None)

            return

        self._business_repo.update(business.id, go_live)
        # The given copy shows the activation too, but keeps the revision it
        # was read with: it does not hold what others saved meanwhile.
        go_live(business)

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
                # The phone instruction; a version assembled before it
                # existed keeps using its chat instruction.
                prompt_text=version.phone_prompt_text or version.prompt_text,
                greetings=self._build_greetings(business, version),
                tools=self._assistant_tool_catalog.list_definitions(version.tools),
                tool_webhook_base_url=base_url,
                transfer_phone_number=find_transfer_phone_number(
                    business,
                    self._business_profile_repo.get_by_business(business.id),
                ),
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
