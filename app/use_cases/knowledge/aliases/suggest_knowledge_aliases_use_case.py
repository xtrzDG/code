from typed_time_provider import Microseconds, WallClock

from app.contracts.knowledge_aliases import KnowledgeAliasSuggesterContract
from app.contracts.localization_utilities import LanguageDetectorContract
from app.contracts.repositories.billing_repositories import UsageEventRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.spend import OwnerAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge_admin import KnowledgeItemDetails
from app.schemas.dto.knowledge_aliases import (
    AliasSuggestionItem,
    SuggestKnowledgeAliasesCommand,
)
from app.schemas.dto.spend_guard import OwnerActionAdmission
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.knowledge.aliases.alias_rounds import (
    plan_alias_items,
    run_alias_round,
)
from app.use_cases.shared.business_access import require_business
from app.utilities.knowledge.knowledge_item_views import to_item_details


class SuggestKnowledgeAliasesUseCase(
    UseCaseContract[SuggestKnowledgeAliasesCommand, KnowledgeItemDetails]
):
    """
    "Suggest translations" in the knowledge editor: one model call names
    the item in the business's languages it has no alias in yet, and the
    suggestions are stored for the owner to review (accept, edit or
    remove; none is a starter question before it is accepted).

    An item that has an alias in every language of the business costs no
    call. A call is an owner action limited per business
    (`OwnerAction.ALIAS_SUGGESTION`) and recorded as usage. An item of
    another business is reported as missing.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        resource_repo: ResourceRepoContract,
        usage_event_repo: UsageEventRepoContract,
        alias_suggester: KnowledgeAliasSuggesterContract,
        language_detector: LanguageDetectorContract,
        admit_owner_action: UseCaseContract[OwnerActionAdmission, None],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._alias_suggester: KnowledgeAliasSuggesterContract = alias_suggester
        self._language_detector: LanguageDetectorContract = language_detector
        self._admit_owner_action: UseCaseContract[OwnerActionAdmission, None] = (
            admit_owner_action
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SuggestKnowledgeAliasesCommand) -> KnowledgeItemDetails:
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        item: KnowledgeItemDocument | None = self._knowledge_item_repo.get(
            business.id, input_data.item_id
        )
        if item is None:
            raise NotFoundError(f"Knowledge item {input_data.item_id} was not found.")

        planned: list[AliasSuggestionItem] = plan_alias_items(
            # Asked for explicitly: a switched-off item or a draft too.
            [item.model_copy(update={"is_active": True, "import_batch_id": None})],
            business,
            self._language_detector,
        )
        if planned:
            self._admit_owner_action.run(
                OwnerActionAdmission(
                    action=OwnerAction.ALIAS_SUGGESTION,
                    user_id=input_data.user_id,
                    business_id=business.id,
                )
            )
            run_alias_round(
                self._alias_suggester,
                self._knowledge_item_repo,
                self._usage_event_repo,
                business,
                planned,
                self._wall_clock.now_unix(),
            )
            item = self._knowledge_item_repo.get(business.id, item.id) or item

        return to_item_details(
            item,
            business.currency_code,
            input_data.language or business.owner_language,
            self._resource_repo.list_by_business(business.id),
        )
