from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import AssistantToolName, AssistantVersionStatus
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.assistants.assistant_commands import (
    AssembleAssistantVersionCommand,
    AssembleAssistantVersionRequest,
)
from app.schemas.dto.assistants.assistant_drafts import (
    AssistantDraft,
    AssistantDraftRequest,
)
from app.schemas.dto.assistants.assistant_views import AssistantVersionDetails
from app.schemas.dto.niches import NicheTemplate
from app.schemas.typings.assistants.constrained_integers import AssistantVersionNumber
from app.use_cases.shared.knowledge_index_queue import queue_knowledge_index
from app.utilities.assembly.autotest_scenarios import (
    list_applicable_kinds,
    select_kinds,
    select_languages,
)


class AssembleAssistantVersionUseCase(
    UseCaseContract[AssembleAssistantVersionCommand, AssistantVersionDetails]
):
    """
    Owner assembles a new assistant version from the current profile
    (concept section 4, "buildAssistant").

    The version stores the draft built from the business as it is now (see
    BuildAssistantDraftUseCase): fact table, instructions, tools and voice.
    It gets the next number, the configured chat model, status DRAFT and
    the profile's revision. Every edit creates a new version; nothing is
    changed in place. A business still onboarding moves to TESTING.

    Autotest languages and kinds in the request are validated here, before
    anything is stored, so a later autotest phase cannot fail on them. The
    knowledge is indexed in the background (`index_knowledge`: aliases in
    the business's other languages, embeddings for the hybrid search).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        business_repo: BusinessRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        build_assistant_draft: UseCaseContract[AssistantDraftRequest, AssistantDraft],
        version_details_transformer: TransformerContract[
            AssistantVersionDocument,
            AssistantVersionDetails,
        ],
        app_settings: AppSettings,
        job_queue: JobQueueFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._business_repo: BusinessRepoContract = business_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._build_assistant_draft: UseCaseContract[
            AssistantDraftRequest, AssistantDraft
        ] = build_assistant_draft
        self._version_details_transformer: TransformerContract[
            AssistantVersionDocument,
            AssistantVersionDetails,
        ] = version_details_transformer
        self._app_settings: AppSettings = app_settings
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(
        self, input_data: AssembleAssistantVersionCommand
    ) -> AssistantVersionDetails:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
                # Done-for-you setup: support may, with the owner's consent.
                support_may_change=True,
            )
        )
        draft: AssistantDraft = self._build_assistant_draft.run(
            AssistantDraftRequest(business=business)
        )
        self._validate_autotest_selection(
            input_data.request,
            business,
            draft.instruction_source.niche,
            draft.tools,
        )
        now: Microseconds = self._wall_clock.now_unix()
        version = AssistantVersionDocument(
            business_id=business.id,
            version_number=self._next_version_number(business),
            status=AssistantVersionStatus.DRAFT,
            niche_key=business.niche_key,
            model_id=self._app_settings.llm_model_id,
            prompt_text=draft.prompt_text,
            phone_prompt_text=draft.phone_prompt_text,
            tools=draft.tools,
            languages=list(business.languages),
            default_language=business.default_language,
            is_voice_enabled=draft.is_voice_enabled,
            facts=draft.facts,
            profile_revision=draft.profile_revision,
            created_at=now,
            updated_at=now,
        )
        self._assistant_version_repo.save(version)
        queue_knowledge_index(self._job_queue, business.id)
        if business.status is BusinessStatus.ONBOARDING:

            def start_testing(current: BusinessDocument) -> None:
                # Changed on the business as stored now, so an edit saved
                # while the version was built is kept.
                if current.status is BusinessStatus.ONBOARDING:
                    current.status = BusinessStatus.TESTING
                    current.updated_at = now

            self._business_repo.update(business.id, start_testing)

        return self._version_details_transformer.transform(version)

    def _next_version_number(
        self, business: BusinessDocument
    ) -> AssistantVersionNumber:
        existing_numbers: list[int] = [
            int(version.version_number)
            for version in self._assistant_version_repo.list_by_business(business.id)
        ]
        return AssistantVersionNumber(max(existing_numbers, default=0) + 1)

    def _validate_autotest_selection(
        self,
        request: AssembleAssistantVersionRequest,
        business: BusinessDocument,
        niche: NicheTemplate,
        tools: list[AssistantToolName],
    ) -> None:
        select_languages(business.languages, request.languages)
        select_kinds(
            list_applicable_kinds(niche.autotest_kinds, tools, business.languages),
            request.kinds,
        )
