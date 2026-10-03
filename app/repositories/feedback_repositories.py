from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.repositories.feedback_repositories import (
    FeedbackRequestChange,
    FeedbackRequestRepoContract,
    ReviewSettingsRepoContract,
)
from app.repositories.aggregate_reading import parse_choice
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    field_equals,
    time_range,
)
from app.schemas.constants.feedback import FeedbackRequestStatus
from app.schemas.domain.feedback import FeedbackRequestDocument, ReviewSettingsDocument
from app.schemas.dto.feedback.feedback_tallies import FeedbackTally
from app.schemas.dto.feedback.review_stats import VisitScoreCount
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_aggregates import (
    DocumentAggregation,
    DocumentFieldBuckets,
    DocumentGroupCount,
)
from app.schemas.dto.storage_queries import DocumentFieldRange, DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.feedback.constrained_integers import (
    FeedbackRequestCount,
    FeedbackScoreTotal,
    VisitScore,
)
from app.schemas.typings.feedback.constrained_strings import ReviewLinkToken
from app.schemas.typings.feedback.prefixed_id import FeedbackRequestId
from app.schemas.typings.storage.booleans import IsDocumentInserted
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger
from app.schemas.typings.storage.strings import DocumentFieldText
from app.utilities.feedback.feedback_keys import review_settings_id_of

IS_FEEDBACK_ENABLED_FIELD: DocumentFieldPath = DocumentFieldPath("is_feedback_enabled")
CONTACT_ID_FIELD: DocumentFieldPath = DocumentFieldPath("contact_id")
STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
REVIEW_TOKEN_FIELD: DocumentFieldPath = DocumentFieldPath("review_token")
SCORE_FIELD: DocumentFieldPath = DocumentFieldPath("score")
REVIEW_CLICKS_FIELD: DocumentFieldPath = DocumentFieldPath("review_clicks")
SCORES: tuple[int, ...] = (1, 2, 3, 4, 5)


class ReviewSettingsRepository(
    BusinessScopedRepository[ReviewSettingsDocument],
    ReviewSettingsRepoContract,
):
    """One settings document per business, keyed by the derived id."""

    def get_by_business(self, business_id: BusinessId) -> ReviewSettingsDocument | None:
        return self._load(business_id, str(review_settings_id_of(business_id)))

    def save(self, settings: ReviewSettingsDocument) -> None:
        self._store(str(settings.id), settings)

    def list_enabled(self) -> list[ReviewSettingsDocument]:
        return self._collection.list_by_fields(
            (field_equals(IS_FEEDBACK_ENABLED_FIELD, True),)
        )


class FeedbackRequestRepository(
    BusinessScopedRepository[FeedbackRequestDocument],
    FeedbackRequestRepoContract,
):
    """
    Requests for feedback, keyed by the id derived from the business and
    the booking; looked up by customer and status, by review token, and
    paged and counted by `created_at` (indexed, migration 1062).
    """

    def insert_if_new(self, request: FeedbackRequestDocument) -> IsDocumentInserted:
        return self._collection.insert_if_absent(str(request.id), request)

    def get(
        self,
        business_id: BusinessId,
        request_id: FeedbackRequestId,
    ) -> FeedbackRequestDocument | None:
        return self._load(business_id, str(request_id))

    def get_many(
        self,
        business_id: BusinessId,
        request_ids: Sequence[FeedbackRequestId],
    ) -> dict[FeedbackRequestId, FeedbackRequestDocument]:
        return {
            request.id: request
            for request in self._load_many(
                business_id, [str(request_id) for request_id in request_ids]
            )
        }

    def update(
        self,
        business_id: BusinessId,
        request_id: FeedbackRequestId,
        change: FeedbackRequestChange,
    ) -> FeedbackRequestDocument | None:
        return self._modify_in_business(business_id, str(request_id), change)

    def list_waiting(
        self,
        business_id: BusinessId,
        contact_id: ContactId,
    ) -> list[FeedbackRequestDocument]:
        waiting: list[FeedbackRequestDocument] = self._list_in_business(
            business_id,
            [
                field_equals(CONTACT_ID_FIELD, contact_id),
                field_equals(STATUS_FIELD, FeedbackRequestStatus.SENT),
            ],
        )
        return sorted(
            waiting, key=lambda request: int(request.created_at), reverse=True
        )

    def find_by_token(self, token: ReviewLinkToken) -> FeedbackRequestDocument | None:
        return self._collection.find_one_by_field(
            REVIEW_TOKEN_FIELD, DocumentFieldText(str(token))
        )

    def page_by_business(
        self,
        business_id: BusinessId,
        window: KeysetSlice,
    ) -> list[FeedbackRequestDocument]:
        return self._page_in_business(business_id, (CREATED_AT_FIELD,), window)

    def tally(
        self,
        business_id: BusinessId,
        created_from: Microseconds,
    ) -> FeedbackTally:
        period: DocumentFieldRange = time_range(
            CREATED_AT_FIELD, starting_at=created_from
        )
        by_status: list[DocumentGroupCount] = self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(ranges=(period,)),
                group_by=(STATUS_FIELD,),
                totals_of=(SCORE_FIELD,),
            ),
        )
        by_score: list[DocumentGroupCount] = self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(
                    matches=(
                        field_equals(STATUS_FIELD, FeedbackRequestStatus.ANSWERED),
                    ),
                    ranges=(period,),
                ),
                buckets=DocumentFieldBuckets(
                    field=SCORE_FIELD,
                    starts=tuple(DocumentFieldInteger(score) for score in SCORES),
                ),
            ),
        )
        opened: list[DocumentGroupCount] = self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(
                    ranges=(
                        period,
                        DocumentFieldRange(
                            field=REVIEW_CLICKS_FIELD, lower=DocumentFieldInteger(1)
                        ),
                    )
                )
            ),
        )
        return FeedbackTally(
            status_counts=count_by_status(by_status),
            score_total=FeedbackScoreTotal(
                sum(int(group.totals[0]) for group in by_status if group.totals)
            ),
            score_counts=count_by_score(by_score),
            opened_count=FeedbackRequestCount(
                sum(int(group.count) for group in opened)
            ),
        )


def count_by_status(
    groups: Sequence[DocumentGroupCount],
) -> dict[FeedbackRequestStatus, FeedbackRequestCount]:
    counts: dict[FeedbackRequestStatus, FeedbackRequestCount] = {}
    for group in groups:
        status: FeedbackRequestStatus | None = parse_choice(
            FeedbackRequestStatus, group.values[0]
        )
        if status is not None:
            counts[status] = FeedbackRequestCount(int(group.count))

    return counts


def count_by_score(groups: Sequence[DocumentGroupCount]) -> list[VisitScoreCount]:
    """One count per score 1 to 5 (zero for a score nobody gave)."""

    counts: dict[int, int] = {
        int(group.bucket): int(group.count)
        for group in groups
        if group.bucket is not None
    }
    return [
        VisitScoreCount(
            score=VisitScore(score),
            count=FeedbackRequestCount(counts.get(index, 0)),
        )
        for index, score in enumerate(SCORES)
    ]
