"""
A business that writes in English and serves Georgian, Russian and Hebrew
customers: its knowledge, the alias model and embedder fakes, and the use
cases of the cross-language search wired over in-memory storage.
"""

from collections.abc import Sequence

from app.adapters.embeddings.in_memory_knowledge_embedding_store_adapter import (
    InMemoryKnowledgeEmbeddingStoreAdapter,
)
from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.repositories.billing_repositories import UsageEventRepository
from app.schemas.constants.knowledge import KnowledgeAliasStatus, KnowledgeItemKind
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.knowledge import KnowledgeAlias, KnowledgeItemDocument
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.knowledge import KnowledgeSearchRequest
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.knowledge.constrained_strings import KnowledgeAliasText
from app.schemas.typings.knowledge.strings import (
    KnowledgeBody,
    KnowledgeSearchQuery,
    KnowledgeTitle,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.knowledge.aliases.suggest_knowledge_aliases_use_case import (
    SuggestKnowledgeAliasesUseCase,
)
from app.use_cases.knowledge.embedding_search_knowledge_use_case import (
    EmbeddingSearchKnowledgeUseCase,
)
from app.use_cases.knowledge.index_knowledge_use_case import IndexKnowledgeUseCase
from app.use_cases.knowledge.search_knowledge_use_case import SearchKnowledgeUseCase
from app.use_cases.spend_guard.admit_owner_action_use_case import (
    AdmitOwnerActionUseCase,
)
from app.utilities.conversations.language_detector import LanguageDetector
from tests.foundation.brand_repositories import in_memory_brand_knowledge_repo
from tests.knowledge.cross_language.fakes import (
    ConceptEmbedder,
    PhraseBookAliasSuggester,
)
from tests.knowledge.knowledge_store import KnowledgeStore

type AliasSpec = tuple[str, str, KnowledgeAliasStatus]


class CrossLanguageWorld(KnowledgeStore):
    """In-memory storage, fakes and the cross-language use cases."""

    def __init__(
        self,
        languages: tuple[str, ...] = ("en", "ka", "ru", "he"),
        suggester: PhraseBookAliasSuggester | None = None,
    ) -> None:
        super().__init__()
        self.owner_id: UserId = UserId()
        self.business = self.add_business(
            languages=languages, owner_language="en", owner_id=self.owner_id
        )
        self.brand_knowledge_repo = in_memory_brand_knowledge_repo()
        self.usage_event_repo = UsageEventRepository(
            InMemoryDocumentCollectionAdapter[UsageEventDocument](UsageEventDocument)
        )
        self.suggester = (
            suggester if suggester is not None else PhraseBookAliasSuggester()
        )
        self.embedder = ConceptEmbedder()
        self.embedding_store = InMemoryKnowledgeEmbeddingStoreAdapter()
        self.language_detector = LanguageDetector()
        self.lexical_search = SearchKnowledgeUseCase(
            business_repo=self.business_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            brand_knowledge_item_repo=self.brand_knowledge_repo,
        )
        self.hybrid_search = EmbeddingSearchKnowledgeUseCase(
            business_repo=self.business_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            brand_knowledge_item_repo=self.brand_knowledge_repo,
            text_embedder=self.embedder,
            embedding_store=self.embedding_store,
        )
        self.suggest_aliases = SuggestKnowledgeAliasesUseCase(
            business_repo=self.business_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            resource_repo=self.resource_repo,
            usage_event_repo=self.usage_event_repo,
            alias_suggester=self.suggester,
            language_detector=self.language_detector,
            admit_owner_action=AdmitOwnerActionUseCase(
                RequestRateLimitRegistry(InMemoryRateLimitBucketAdapter()),
                self.wall_clock,
            ),
            wall_clock=self.wall_clock,
        )
        self.index_knowledge = IndexKnowledgeUseCase(
            business_repo=self.business_repo,
            knowledge_item_repo=self.knowledge_item_repo,
            brand_knowledge_item_repo=self.brand_knowledge_repo,
            usage_event_repo=self.usage_event_repo,
            alias_suggester=self.suggester,
            language_detector=self.language_detector,
            text_embedder=self.embedder,
            embedding_store=self.embedding_store,
            wall_clock=self.wall_clock,
        )

    def add_item(
        self,
        title: str,
        kind: KnowledgeItemKind = KnowledgeItemKind.FAQ,
        body: str | None = None,
        languages: Sequence[str] = ("en",),
        aliases: Sequence[AliasSpec] = (),
        is_active: bool = True,
        price_minor: int | None = None,
    ) -> KnowledgeItemDocument:
        now = self.wall_clock.now_unix()
        item = KnowledgeItemDocument(
            business_id=self.business.id,
            kind=kind,
            title=KnowledgeTitle(title),
            body=None if body is None else KnowledgeBody(body),
            price_minor=None if price_minor is None else MoneyAmountMinor(price_minor),
            currency_code=None if price_minor is None else self.business.currency_code,
            languages=[LanguageTag(language) for language in languages],
            aliases=[
                KnowledgeAlias(
                    language=LanguageTag(language),
                    text=KnowledgeAliasText(text),
                    status=status,
                )
                for language, text, status in aliases
            ],
            is_active=is_active,
            created_at=now,
            updated_at=now,
        )
        self.knowledge_item_repo.save(item)
        return item

    def item(self, item: KnowledgeItemDocument) -> KnowledgeItemDocument:
        stored = self.knowledge_item_repo.get(self.business.id, item.id)
        assert stored is not None
        return stored

    def run_index(self, is_final_attempt: bool = False) -> JobReport:
        return self.index_knowledge.run(
            QueuedJobInput(
                job_id=QueuedJobId(),
                job_name=JobName("index_knowledge"),
                payload=JobPayloadJson("{}"),
                business_id=self.business.id,
                is_final_attempt=is_final_attempt,
            )
        )

    def search(self, query: str, language: str, hybrid: bool = True) -> list[str]:
        search = self.hybrid_search if hybrid else self.lexical_search
        result = search.run(
            KnowledgeSearchRequest(
                business_id=self.business.id,
                query=KnowledgeSearchQuery(query),
                language=LanguageTag(language),
            )
        )
        return [str(item.title) for item in result.items]
