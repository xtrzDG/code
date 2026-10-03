"""
The feedback repositories on both storages: a visit is asked about once,
the review token is found across businesses only platform-wide, the
waiting requests and the statistics of a business, and the settings of
every business with feedback on (the periodic job's list).
"""

from typed_time_provider import Microseconds

from app.repositories.feedback_repositories import (
    FeedbackRequestRepository,
    ReviewSettingsRepository,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.feedback import FeedbackRequestStatus
from app.schemas.domain.feedback import FeedbackRequestDocument, ReviewSettingsDocument
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.feedback.constrained_integers import (
    ReviewLinkClickCount,
    VisitScore,
)
from app.schemas.typings.feedback.constrained_strings import ReviewLinkToken
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.feedback.feedback_keys import (
    feedback_request_id_of,
    review_settings_id_of,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import CollectionFactory

TOKEN = ReviewLinkToken("q3Jd8sLq0Pz-Xb7W2nVc1A")
NOW: int = 1_790_000_000_000_000
HOUR: int = 3_600_000_000


def build_request(
    business_id: BusinessId,
    contact_id: ContactId,
    status: FeedbackRequestStatus,
    hours_ago: int = 1,
    score: int | None = None,
    clicks: int = 0,
    token: ReviewLinkToken | None = None,
) -> FeedbackRequestDocument:
    moment = Microseconds(NOW - hours_ago * HOUR)
    booking_id = BookingId()
    return FeedbackRequestDocument(
        id=feedback_request_id_of(business_id, booking_id),
        business_id=business_id,
        booking_id=booking_id,
        contact_id=contact_id,
        visit_ended_at=moment,
        language=LanguageTag("ka"),
        status=status,
        channel=ChannelKind.WHATSAPP,
        review_token=token,
        sent_at=moment,
        score=None if score is None else VisitScore(score),
        review_clicks=ReviewLinkClickCount(clicks),
        created_at=moment,
        updated_at=moment,
    )


def test_requests_are_asked_once_and_found_by_their_token(
    collections: CollectionFactory, storage_scope: StorageScopeContext
) -> None:
    requests = FeedbackRequestRepository(
        collections(FeedbackRequestDocument, "feedback_requests")
    )
    business_id, other_business_id = BusinessId(), BusinessId()
    request = build_request(
        business_id, ContactId(), FeedbackRequestStatus.SENT, token=TOKEN
    )

    with storage_scope.scoped_to_business(business_id):
        assert requests.insert_if_new(request) is True
        assert requests.insert_if_new(request) is False
    with storage_scope.scoped_to_business(other_business_id):
        assert requests.get_many(other_business_id, [request.id]) == {}
    with storage_scope.platform_wide():
        found = requests.find_by_token(TOKEN)
        missing = requests.find_by_token(ReviewLinkToken("A" * 22))

    assert found is not None
    assert found.id == request.id
    assert missing is None


def test_waiting_requests_and_the_numbers_of_a_business(
    collections: CollectionFactory, storage_scope: StorageScopeContext
) -> None:
    requests = FeedbackRequestRepository(
        collections(FeedbackRequestDocument, "feedback_requests")
    )
    business_id, contact_id = BusinessId(), ContactId()
    older = build_request(business_id, contact_id, FeedbackRequestStatus.SENT, 30)
    newer = build_request(business_id, contact_id, FeedbackRequestStatus.SENT, 2)
    stored = [
        older,
        newer,
        build_request(business_id, contact_id, FeedbackRequestStatus.ANSWERED, 3, 5, 2),
        build_request(business_id, ContactId(), FeedbackRequestStatus.ANSWERED, 4, 2),
        build_request(business_id, ContactId(), FeedbackRequestStatus.SKIPPED, 5),
        build_request(
            business_id, ContactId(), FeedbackRequestStatus.ANSWERED, 24 * 40, 1, 1
        ),
    ]

    with storage_scope.scoped_to_business(business_id):
        for request in stored:
            requests.insert_if_new(request)
        waiting = requests.list_waiting(business_id, contact_id)
        tally = requests.tally(business_id, Microseconds(NOW - 24 * 30 * HOUR))

    assert [request.id for request in waiting] == [newer.id, older.id]
    assert {status: int(count) for status, count in tally.status_counts.items()} == {
        FeedbackRequestStatus.SENT: 2,
        FeedbackRequestStatus.ANSWERED: 2,
        FeedbackRequestStatus.SKIPPED: 1,
    }
    assert int(tally.score_total) == 7
    assert [(int(item.score), int(item.count)) for item in tally.score_counts] == [
        (1, 0),
        (2, 1),
        (3, 0),
        (4, 0),
        (5, 1),
    ]
    assert int(tally.opened_count) == 1


def test_the_job_lists_every_business_with_feedback_on(
    collections: CollectionFactory, storage_scope: StorageScopeContext
) -> None:
    settings = ReviewSettingsRepository(
        collections(ReviewSettingsDocument, "review_settings")
    )
    on, off = BusinessId(), BusinessId()
    now = Microseconds(NOW)
    for business_id, is_enabled in ((on, True), (off, False)):
        with storage_scope.scoped_to_business(business_id):
            settings.save(
                ReviewSettingsDocument(
                    id=review_settings_id_of(business_id),
                    business_id=business_id,
                    is_feedback_enabled=is_enabled,
                    created_at=now,
                    updated_at=now,
                )
            )

    with storage_scope.platform_wide():
        enabled = settings.list_enabled()

    assert [item.business_id for item in enabled] == [on]
