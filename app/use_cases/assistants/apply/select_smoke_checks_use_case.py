from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.setup import PendingChangeAction, PendingChangeArea
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.assistants.smoke_checks import SmokeCheckSelection
from app.schemas.dto.niches import NicheTemplate
from app.schemas.dto.setup.apply_changes import AppliedVersion
from app.schemas.dto.setup.pending_changes import PendingChange
from app.schemas.exceptions.application_errors import NotFoundError
from app.utilities.assembly.autotest_scenarios import list_applicable_kinds
from app.utilities.assembly.fact_diff import diff_fact_tables
from app.utilities.assembly.fact_formatting import compute_local_date
from app.utilities.assembly.smoke_selection import select_smoke_checks


class SelectSmokeChecksUseCase(
    UseCaseContract[AppliedVersion, SmokeCheckSelection | None]
):
    """
    Which checks the version an apply built must pass. Before the first
    go-live: every scenario in every language (None). After it: the quick
    check of what this version changes against the live one (see
    `select_smoke_checks`): its fact rows, its instruction and its phone
    line, so an owner who changed a price waits for a handful of
    conversations, not for all of them.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AppliedVersion) -> SmokeCheckSelection | None:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        version: AssistantVersionDocument | None = self._assistant_version_repo.get(
            input_data.business_id, input_data.assistant_version_id
        )
        if business is None or version is None:
            raise NotFoundError(
                f"Assistant version {input_data.assistant_version_id} was not found."
            )

        live: AssistantVersionDocument | None = (
            None
            if business.published_assistant_version_id is None
            else self._assistant_version_repo.get(
                business.id, business.published_assistant_version_id
            )
        )
        if live is None:
            return None

        niche: NicheTemplate = self._niche_template_registry.get(version.niche_key)
        applicable_kinds: list[AutotestScenarioKind] = list_applicable_kinds(
            niche.autotest_kinds, version.tools, version.languages
        )
        return select_smoke_checks(
            self._version_changes(business, live, version),
            applicable_kinds,
            version.languages,
            version.default_language,
            {
                str(item.title)
                for item in self._knowledge_item_repo.list_by_business(business.id)
                if item.is_active and item.price_minor is not None
            },
        )

    def _version_changes(
        self,
        business: BusinessDocument,
        live: AssistantVersionDocument,
        version: AssistantVersionDocument,
    ) -> list[PendingChange]:
        changes: list[PendingChange] = diff_fact_tables(
            live.facts,
            version.facts,
            compute_local_date(self._wall_clock.now_unix(), business.timezone),
            {},
        )
        if version.is_voice_enabled != live.is_voice_enabled:
            changes.append(
                PendingChange(
                    area=PendingChangeArea.CALLS, action=PendingChangeAction.CHANGED
                )
            )

        if not changes and version.prompt_text != live.prompt_text:
            changes.append(
                PendingChange(
                    area=PendingChangeArea.CONVERSATION,
                    action=PendingChangeAction.CHANGED,
                )
            )

        return changes
