import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.knowledge_aliases import KnowledgeAliasSuggesterContract
from app.contracts.knowledge_embeddings import (
    KnowledgeEmbeddingStoreContract,
    TextEmbedderContract,
)
from app.contracts.localization_utilities import LanguageDetectorContract
from app.contracts.repositories.billing_repositories import UsageEventRepoContract
from app.contracts.repositories.brand_repositories import (
    BrandKnowledgeItemRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.knowledge_aliases import AliasSuggestionItem
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.knowledge.aliases.alias_rounds import (
    MAX_ITEMS_PER_CALL,
    AliasRoundOutcome,
    plan_alias_items,
    run_alias_round,
)
from app.use_cases.knowledge.knowledge_embedding_refresh import (
    EmbeddingRefreshOutcome,
    refresh_embeddings,
)
from app.use_cases.shared.assistant_knowledge import load_active_knowledge

LOGGER: logging.Logger = logging.getLogger(__name__)
# One run names at most this many calls' worth of items (200); a bigger
# knowledge base gets the rest at the next assembly or import.
MAX_ALIAS_CALLS_PER_RUN: int = 5


class IndexKnowledgeUseCase(UseCaseContract[QueuedJobInput, JobReport]):
    """
    The worker's `index_knowledge` job, queued when a version is assembled
    or an import is confirmed: keeps a business's knowledge findable in
    every language of the business.

    1. Aliases: active, confirmed items without an alias in one of the
       business's languages are named in them by the model, up to 40 items
       per call (questions first, they become starter questions), stored
       as suggestions for the owner to review and recorded as usage.
    2. Embeddings (EMBEDDINGS_API_KEY and pgvector): the vectors of the
       active knowledge, the brand's shared facts included, are made
       current (`refresh_embeddings`).

    A failed alias call does not stop the embeddings; the job then fails so
    the queue retries it (a retry asks only for what is still missing),
    except on its last attempt.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        brand_knowledge_item_repo: BrandKnowledgeItemRepoContract,
        usage_event_repo: UsageEventRepoContract,
        alias_suggester: KnowledgeAliasSuggesterContract,
        language_detector: LanguageDetectorContract,
        text_embedder: TextEmbedderContract,
        embedding_store: KnowledgeEmbeddingStoreContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._brand_knowledge_item_repo: BrandKnowledgeItemRepoContract = (
            brand_knowledge_item_repo
        )
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._alias_suggester: KnowledgeAliasSuggesterContract = alias_suggester
        self._language_detector: LanguageDetectorContract = language_detector
        self._text_embedder: TextEmbedderContract = text_embedder
        self._embedding_store: KnowledgeEmbeddingStoreContract = embedding_store
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: QueuedJobInput) -> JobReport:
        if input_data.business_id is None:
            return JobReport()

        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            return JobReport()

        alias_failure: ExternalServiceError | None = None
        named: int = 0
        try:
            named = self._suggest_aliases(business)
        except ExternalServiceError as error:
            alias_failure = error
            LOGGER.warning(
                "Alias suggestions failed for business %s (%s).",
                business.id,
                type(error).__name__,
            )

        refreshed: EmbeddingRefreshOutcome = refresh_embeddings(
            self._text_embedder,
            self._embedding_store,
            business.id,
            load_active_knowledge(
                self._knowledge_item_repo, self._brand_knowledge_item_repo, business
            ),
        )
        LOGGER.info(
            "Knowledge index of business %s: %d items named, %d embedded, "
            "%d vectors forgotten.",
            business.id,
            named,
            refreshed.embedded_count,
            refreshed.forgotten_count,
        )
        if alias_failure is not None and not input_data.is_final_attempt:
            raise alias_failure

        return JobReport(
            processed_count=ProcessedItemCount(named + refreshed.embedded_count)
        )

    def _suggest_aliases(self, business: BusinessDocument) -> int:
        """Items that got new aliases, over at most `MAX_ALIAS_CALLS_PER_RUN` calls."""

        planned: list[AliasSuggestionItem] = plan_alias_items(
            self._knowledge_item_repo.list_by_business(business.id),
            business,
            self._language_detector,
        )
        named: int = 0
        for call in range(MAX_ALIAS_CALLS_PER_RUN):
            batch: list[AliasSuggestionItem] = planned[
                call * MAX_ITEMS_PER_CALL : (call + 1) * MAX_ITEMS_PER_CALL
            ]
            if batch == []:
                break

            outcome: AliasRoundOutcome = run_alias_round(
                self._alias_suggester,
                self._knowledge_item_repo,
                self._usage_event_repo,
                business,
                batch,
                self._wall_clock.now_unix(),
            )
            named += outcome.updated_count

        return named
