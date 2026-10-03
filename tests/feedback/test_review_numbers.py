"""
The numbers of Settings → Reviews (asked, answered, average, review link
opened over the last 30 days), the latest requests, and the public review
link that counts a customer's visit before sending them on to Google.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.feedback import FeedbackRequestStatus, FeedbackSkipReason
from app.schemas.domain.feedback import FeedbackRequestDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.feedback.constrained_integers import (
    ReviewLinkClickCount,
    VisitScore,
)
from app.schemas.typings.feedback.constrained_strings import ReviewLinkToken
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.feedback.feedback_keys import feedback_request_id_of
from tests.channels.channels_payloads import bearer
from tests.feedback.feedback_http import build_feedback_http_client
from tests.feedback.feedback_setup import FeedbackSetup

REVIEW_PAGE: str = "https://g.page/r/rustaveli/review"
TOKEN: str = "q3Jd8sLq0Pz-Xb7W2nVc1A"
DAY_MICROSECONDS: int = 86_400_000_000


def add_request(
    setup: FeedbackSetup,
    status: FeedbackRequestStatus,
    score: int | None = None,
    clicks: int = 0,
    days_ago: int = 1,
    contact_id: ContactId | None = None,
    token: str | None = None,
) -> FeedbackRequestDocument:
    moment = Microseconds(
        int(setup.testbed.clock.now_microseconds()) - days_ago * DAY_MICROSECONDS
    )
    booking_id = BookingId()
    request = FeedbackRequestDocument(
        id=feedback_request_id_of(setup.business.id, booking_id),
        business_id=setup.business.id,
        booking_id=booking_id,
        contact_id=contact_id or ContactId(),
        visit_ended_at=moment,
        language=LanguageTag("ka"),
        status=status,
        skip_reason=(
            FeedbackSkipReason.OPTED_OUT
            if status is FeedbackRequestStatus.SKIPPED
            else None
        ),
        channel=None
        if status is FeedbackRequestStatus.SKIPPED
        else ChannelKind.WHATSAPP,
        review_token=None if token is None else ReviewLinkToken(token),
        sent_at=None if status is FeedbackRequestStatus.SKIPPED else moment,
        score=None if score is None else VisitScore(score),
        answered_at=None if score is None else moment,
        review_clicks=ReviewLinkClickCount(clicks),
        created_at=moment,
        updated_at=moment,
    )
    setup.testbed.feedback_request_repo.insert_if_new(request)
    return request


def add_profile(setup: FeedbackSetup, review_url: str | None = REVIEW_PAGE) -> None:
    setup.testbed.profile_repo.save(
        BusinessProfileDocument(
            business_id=setup.business.id,
            niche_key=setup.business.niche_key,
            answers_language=setup.business.owner_language,
            google_review_url=None if review_url is None else WebLink(review_url),
        )
    )


@pytest.fixture
def setup() -> FeedbackSetup:
    return FeedbackSetup()


@pytest.fixture
def client(setup: FeedbackSetup) -> TestClient:
    return build_feedback_http_client(setup)


class TestStats:
    def test_the_last_thirty_days_in_numbers(
        self, setup: FeedbackSetup, client: TestClient
    ) -> None:
        add_request(setup, FeedbackRequestStatus.ANSWERED, score=5, clicks=2)
        add_request(setup, FeedbackRequestStatus.ANSWERED, score=5)
        add_request(setup, FeedbackRequestStatus.ANSWERED, score=2, clicks=1)
        add_request(setup, FeedbackRequestStatus.SENT)
        add_request(setup, FeedbackRequestStatus.SKIPPED)
        add_request(setup, FeedbackRequestStatus.FAILED)
        add_request(setup, FeedbackRequestStatus.ANSWERED, score=1, days_ago=40)

        response = client.get(
            f"/v1/businesses/{setup.business.id}/review-stats",
            headers=bearer("owner"),
        )

        assert response.status_code == 200, response.text
        body: dict[str, Any] = response.json()
        assert body["period_days"] == 30
        assert body["asked_count"] == 4
        assert body["answered_count"] == 3
        assert body["average_score"] == 4.0
        assert {item["score"]: item["count"] for item in body["score_counts"]} == {
            1: 0,
            2: 1,
            3: 0,
            4: 0,
            5: 2,
        }
        assert body["review_opened_count"] == 2
        assert body["skipped_count"] == 1
        assert body["failed_count"] == 1

    def test_no_answers_have_no_average(
        self, setup: FeedbackSetup, client: TestClient
    ) -> None:
        add_request(setup, FeedbackRequestStatus.SENT)

        body = client.get(
            f"/v1/businesses/{setup.business.id}/review-stats",
            headers=bearer("owner"),
        ).json()

        assert body["asked_count"] == 1
        assert body["answered_count"] == 0
        assert body["average_score"] is None


class TestLatestRequests:
    def test_newest_first_with_the_customer_and_audited(
        self, setup: FeedbackSetup, client: TestClient
    ) -> None:
        contact = setup.add_customer()
        contact.name = ContactName("Nino")
        setup.testbed.contact_repo.save(contact)
        older = add_request(setup, FeedbackRequestStatus.SKIPPED, days_ago=3)
        newer = add_request(
            setup, FeedbackRequestStatus.ANSWERED, score=4, contact_id=contact.id
        )

        response = client.get(
            f"/v1/businesses/{setup.business.id}/feedback-requests?limit=1",
            headers=bearer("owner"),
        )
        rest = client.get(
            f"/v1/businesses/{setup.business.id}/feedback-requests",
            params={"cursor": response.json()["next_cursor"]},
            headers=bearer("owner"),
        )

        assert response.status_code == 200, response.text
        [first] = response.json()["items"]
        assert first["id"] == str(newer.id)
        assert first["contact_name"] == "Nino"
        assert first["score"] == 4
        assert first["status"] == "answered"
        [second] = rest.json()["items"]
        assert second["id"] == str(older.id)
        assert second["skip_reason"] == "opted_out"
        assert rest.json()["next_cursor"] is None
        assert setup.testbed.audit_actions(setup.business.id)[-1] == (
            "view",
            "feedback_request",
        )


class TestReviewLink:
    def link(self, token: str = TOKEN) -> str:
        return f"/v1/public/reviews/{token}"

    def test_the_link_counts_the_visit_and_goes_to_google(
        self, setup: FeedbackSetup, client: TestClient
    ) -> None:
        add_profile(setup)
        request = add_request(
            setup, FeedbackRequestStatus.ANSWERED, score=5, token=TOKEN
        )

        response = client.get(self.link(), headers={"User-Agent": "Mozilla/5.0"})
        client.get(self.link(), headers={"User-Agent": "Mozilla/5.0"})

        assert response.status_code == 302
        assert response.headers["location"] == REVIEW_PAGE
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-robots-tag"] == "noindex"
        assert response.headers["referrer-policy"] == "no-referrer"
        stored = setup.testbed.feedback_request_repo.get(setup.business.id, request.id)
        assert stored is not None
        assert int(stored.review_clicks) == 2
        assert stored.first_clicked_at == setup.testbed.clock.now_microseconds()

    @pytest.mark.parametrize(
        "agent",
        [
            "WhatsApp/2.23.20.0",
            "TelegramBot (like TwitterBot)",
            "facebookexternalhit/1.1",
        ],
    )
    def test_a_messenger_preview_is_not_counted(
        self, setup: FeedbackSetup, client: TestClient, agent: str
    ) -> None:
        add_profile(setup)
        request = add_request(
            setup, FeedbackRequestStatus.ANSWERED, score=3, token=TOKEN
        )

        response = client.get(self.link(), headers={"User-Agent": agent})

        assert response.status_code == 302
        stored = setup.testbed.feedback_request_repo.get(setup.business.id, request.id)
        assert stored is not None
        assert int(stored.review_clicks) == 0

    @pytest.mark.parametrize("token", ["A" * 22, "short", "q3Jd8sLq0Pz-Xb7W2nVc1A!"])
    def test_an_unknown_token_is_not_found(
        self, setup: FeedbackSetup, client: TestClient, token: str
    ) -> None:
        add_profile(setup)
        add_request(setup, FeedbackRequestStatus.ANSWERED, score=5, token=TOKEN)

        response = client.get(self.link(token))

        assert response.status_code == 404

    def test_a_removed_review_page_is_not_found(
        self, setup: FeedbackSetup, client: TestClient
    ) -> None:
        add_profile(setup, review_url=None)
        add_request(setup, FeedbackRequestStatus.ANSWERED, score=5, token=TOKEN)

        response = client.get(self.link())

        assert response.status_code == 404
