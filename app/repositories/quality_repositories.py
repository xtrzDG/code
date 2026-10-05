"""Production quality: the judge's scores of real conversations and their sums."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.quality_repositories import (
    ConversationQualityRepoContract,
    QualitySampleInputRepoContract,
    QualityTotalsRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.conversation_lookup_fields import LAST_MESSAGE_AT_FIELD
from app.repositories.document_queries import (
    of_business,
    time_range,
    without_sandbox,
)
from app.schemas.domain.conversation_quality import ConversationQualityScoreDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.platform_health import ActivityWindow
from app.schemas.dto.quality import QualityTotals
from app.schemas.dto.storage_aggregates import (
    DocumentAggregation,
    DocumentFieldBuckets,
    DocumentGroupCount,
)
from app.schemas.dto.storage_pages import DocumentPageQuery
from app.schemas.dto.storage_queries import DocumentFieldRange, DocumentFilter
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.quality.constrained_integers import (
    QualitySampleCount,
    QualityScoreHundredthsTotal,
)
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentQueryLimit,
)
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger
from app.utilities.quality.quality_sampling import quality_score_id_of

JUDGED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("judged_at")
SCORE_FIELD: DocumentFieldPath = DocumentFieldPath("score_hundredths")
COST_FIELD: DocumentFieldPath = DocumentFieldPath("cost_micro_usd")
SUMMED_FIELDS: tuple[DocumentFieldPath, ...] = (SCORE_FIELD, COST_FIELD)


class ConversationQualityRepository(
    BusinessScopedRepository[ConversationQualityScoreDocument],
    ConversationQualityRepoContract,
):
    """
    One score per conversation (the derived id); a business's days summed
    by the database over `(business_id, doc_judged_at)` (1120).
    """

    def get(
        self, business_id: BusinessId, conversation_id: ConversationId
    ) -> ConversationQualityScoreDocument | None:
        return self._load(business_id, str(quality_score_id_of(conversation_id)))

    def save(self, score: ConversationQualityScoreDocument) -> None:
        self._store(str(score.id), score)

    def sum_days(
        self,
        business_id: BusinessId,
        day_starts: Sequence[Microseconds],
        until: Microseconds,
    ) -> list[QualityTotals]:
        groups: list[DocumentGroupCount] = self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(ranges=(judged_within(day_starts[0], until),)),
                buckets=DocumentFieldBuckets(
                    field=JUDGED_AT_FIELD,
                    starts=tuple(DocumentFieldInteger(int(day)) for day in day_starts),
                ),
                totals_of=SUMMED_FIELDS,
            ),
        )
        by_bucket: dict[int, DocumentGroupCount] = {
            int(group.bucket): group for group in groups if group.bucket is not None
        }
        return [
            to_totals(by_bucket[index]) if index in by_bucket else QualityTotals()
            for index in range(len(day_starts))
        ]

    def list_lowest(
        self,
        business_id: BusinessId,
        window: ActivityWindow,
        limit: DocumentQueryLimit,
    ) -> list[ConversationQualityScoreDocument]:
        return self._collection.page_by(
            DocumentPageQuery(
                where=DocumentFilter(
                    matches=(of_business(business_id),),
                    ranges=(judged_within(window.since, window.until),),
                ),
                sort_fields=(SCORE_FIELD,),
                is_descending=False,
                limit=limit,
            )
        )


class QualityTotalsRepository(QualityTotalsRepoContract):
    """Across businesses, by the platform-wide `(doc_judged_at)` index (1120)."""

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[ConversationQualityScoreDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            ConversationQualityScoreDocument
        ] = collection

    def sum_judged(self, window: ActivityWindow) -> QualityTotals:
        groups: list[DocumentGroupCount] = self._collection.count_by(
            DocumentAggregation(
                where=DocumentFilter(
                    ranges=(judged_within(window.since, window.until),)
                ),
                totals_of=SUMMED_FIELDS,
            )
        )
        return to_totals(groups[0]) if groups else QualityTotals()

    def delete_judged_before(self, cutoff: Microseconds) -> DocumentCount:
        return self._collection.delete_by_range(
            time_range(JUDGED_AT_FIELD, ending_before=cutoff)
        )


class QualitySampleInputRepository(QualitySampleInputRepoContract):
    """A business's conversations by `(business_id, doc_last_message_at)` (1010)."""

    def __init__(
        self,
        conversation_collection: DocumentCollectionAdapterContract[
            ConversationDocument
        ],
    ) -> None:
        self._conversations: DocumentCollectionAdapterContract[ConversationDocument] = (
            conversation_collection
        )

    def list_recent(
        self,
        business_id: BusinessId,
        window: ActivityWindow,
        limit: DocumentQueryLimit,
    ) -> list[ConversationDocument]:
        return self._conversations.page_by(
            DocumentPageQuery(
                where=DocumentFilter(
                    matches=(of_business(business_id),),
                    excluding=(without_sandbox(),),
                    ranges=(
                        time_range(LAST_MESSAGE_AT_FIELD, window.since, window.until),
                    ),
                ),
                sort_fields=(LAST_MESSAGE_AT_FIELD,),
                limit=limit,
            )
        )


def judged_within(since: Microseconds, until: Microseconds) -> DocumentFieldRange:
    return time_range(JUDGED_AT_FIELD, since, until)


def to_totals(group: DocumentGroupCount) -> QualityTotals:
    score_total, cost_total = (int(total) for total in group.totals)
    return QualityTotals(
        sample_count=QualitySampleCount(int(group.count)),
        score_hundredths_total=QualityScoreHundredthsTotal(score_total),
        cost_micro_usd=CostMicroUsd(cost_total),
    )
