"""
Settings → Reviews over HTTP: the owner's switches and the Google review
link (kept in the profile), the template texts, the last 30 days in
numbers and the latest requests; owners only.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessMember
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.typings.businesses.constrained_strings import WebLink
from tests.channels.channels_payloads import bearer
from tests.feedback.feedback_http import build_feedback_http_client
from tests.feedback.feedback_setup import FeedbackSetup

REVIEW_PAGE: str = "https://g.page/r/rustaveli/review"


def settings_path(setup: FeedbackSetup) -> str:
    return f"/v1/businesses/{setup.business.id}/review-settings"


def add_profile(setup: FeedbackSetup, review_url: str | None = None) -> None:
    setup.testbed.profile_repo.save(
        BusinessProfileDocument(
            business_id=setup.business.id,
            niche_key=setup.business.niche_key,
            answers_language=setup.business.owner_language,
            google_review_url=None if review_url is None else WebLink(review_url),
        )
    )


def stored_review_url(setup: FeedbackSetup) -> str | None:
    profile = setup.testbed.profile_repo.get_by_business(setup.business.id)
    assert profile is not None
    return None if profile.google_review_url is None else str(profile.google_review_url)


@pytest.fixture
def setup() -> FeedbackSetup:
    feedback_setup = FeedbackSetup(has_settings=False)
    staff_id = feedback_setup.testbed.add_user("staff")
    feedback_setup.testbed.add_user("stranger")
    feedback_setup.business.members.append(
        BusinessMember(user_id=staff_id, role=BusinessMemberRole.STAFF)
    )
    feedback_setup.testbed.business_repo.save(feedback_setup.business)
    return feedback_setup


@pytest.fixture
def client(setup: FeedbackSetup) -> TestClient:
    return build_feedback_http_client(setup)


class TestReviewSettings:
    def test_the_defaults(self, setup: FeedbackSetup, client: TestClient) -> None:
        response = client.get(settings_path(setup), headers=bearer("owner"))

        assert response.status_code == 200, response.text
        body: dict[str, Any] = response.json()
        assert body["is_feedback_enabled"] is False
        assert body["delay_minutes"] == 120
        assert body["feedback_template_name"] is None
        assert body["google_review_url"] is None
        assert body["is_whatsapp_connected"] is True
        assert body["is_link_tracked"] is True
        previews = {
            preview["language"]: preview for preview in body["template_previews"]
        }
        assert list(previews) == ["ka", "ru", "en"]
        assert "{{1}}" in previews["en"]["template_body"]
        assert "{business}" not in previews["en"]["template_body"]
        assert "STOP" in previews["en"]["template_body"]
        assert "Café Rustaveli" in previews["ka"]["example"]

    def test_the_owner_turns_feedback_on_with_the_review_link(
        self, setup: FeedbackSetup, client: TestClient
    ) -> None:
        add_profile(setup)

        response = client.put(
            settings_path(setup),
            json={
                "is_feedback_enabled": True,
                "delay_minutes": 180,
                "feedback_template_name": "visit_feedback",
                "google_review_url": REVIEW_PAGE,
            },
            headers=bearer("owner"),
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["is_feedback_enabled"] is True
        assert body["delay_minutes"] == 180
        assert body["feedback_template_name"] == "visit_feedback"
        assert body["google_review_url"] == REVIEW_PAGE
        assert stored_review_url(setup) == REVIEW_PAGE
        stored = setup.review_settings_repo.get_by_business(setup.business.id)
        assert stored is not None
        assert stored.is_feedback_enabled is True
        assert setup.testbed.audit_actions(setup.business.id)[-1] == (
            "update",
            "review_settings",
        )
        again = client.get(settings_path(setup), headers=bearer("owner")).json()
        assert again["google_review_url"] == REVIEW_PAGE

    def test_removing_the_link_clears_it_from_the_profile(
        self, setup: FeedbackSetup, client: TestClient
    ) -> None:
        add_profile(setup, REVIEW_PAGE)

        response = client.put(
            settings_path(setup),
            json={"is_feedback_enabled": True},
            headers=bearer("owner"),
        )

        assert response.status_code == 200, response.text
        assert response.json()["google_review_url"] is None
        assert stored_review_url(setup) is None

    def test_a_link_needs_the_profile_first(
        self, setup: FeedbackSetup, client: TestClient
    ) -> None:
        response = client.put(
            settings_path(setup),
            json={"is_feedback_enabled": True, "google_review_url": REVIEW_PAGE},
            headers=bearer("owner"),
        )

        assert response.status_code == 422
        assert setup.review_settings_repo.get_by_business(setup.business.id) is None

    @pytest.mark.parametrize(
        "body",
        [
            {"delay_minutes": 5},
            {"delay_minutes": 10_000},
            {"google_review_url": "javascript:alert(1)"},
            {"feedback_template_name": "Visit Feedback"},
            {"is_feedback_enabled": "maybe"},
        ],
    )
    def test_malformed_settings_are_refused(
        self, setup: FeedbackSetup, client: TestClient, body: dict[str, Any]
    ) -> None:
        add_profile(setup)

        response = client.put(settings_path(setup), json=body, headers=bearer("owner"))

        assert response.status_code == 422

    def test_without_the_public_address_links_are_not_tracked(
        self, setup: FeedbackSetup
    ) -> None:
        client = build_feedback_http_client(setup, app_base_url=None)

        response = client.get(settings_path(setup), headers=bearer("owner"))

        assert response.json()["is_link_tracked"] is False

    @pytest.mark.parametrize(
        ("method", "suffix"),
        [
            ("GET", "review-settings"),
            ("PUT", "review-settings"),
            ("GET", "review-stats"),
            ("GET", "feedback-requests"),
        ],
    )
    def test_only_owners_see_and_change_them(
        self, setup: FeedbackSetup, client: TestClient, method: str, suffix: str
    ) -> None:
        path = f"/v1/businesses/{setup.business.id}/{suffix}"
        body = {"is_feedback_enabled": True} if method == "PUT" else None

        by_staff = client.request(method, path, json=body, headers=bearer("staff"))
        by_stranger = client.request(
            method, path, json=body, headers=bearer("stranger")
        )
        anonymous = client.request(method, path, json=body)

        assert by_staff.status_code == 403
        assert by_stranger.status_code == 404
        assert anonymous.status_code == 401
