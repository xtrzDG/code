"""
The demo restaurant (SEED_DEMO_DATA) asks its guests about their visits:
Settings → Reviews shows the settings, the Google review link, a month of
answers with their average and the latest requests.
"""

from typing import Any

from tests.demo.test_demo_seeding import (
    DEMO_ENVIRONMENT,
    RESTAURANT,
    businesses_by_name,
    sign_in_owner,
)
from tests.e2e.harness import start_workshop


def test_the_demo_restaurant_has_a_month_of_reviews() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        headers = sign_in_owner(workshop)
        restaurant = businesses_by_name(client, headers)[RESTAURANT]
        base = f"/v1/businesses/{restaurant['id']}"

        settings: dict[str, Any] = client.get(
            f"{base}/review-settings", headers=headers
        ).json()
        stats: dict[str, Any] = client.get(
            f"{base}/review-stats", headers=headers
        ).json()
        requests: dict[str, Any] = client.get(
            f"{base}/feedback-requests?limit=20", headers=headers
        ).json()

    assert settings["is_feedback_enabled"] is True
    assert settings["feedback_template_name"] == "visit_feedback"
    assert str(settings["google_review_url"]).endswith("/review")
    assert stats["answered_count"] >= 3
    assert 1.0 <= stats["average_score"] <= 5.0
    assert stats["review_opened_count"] >= 1
    assert len(requests["items"]) >= 5
    assert {item["status"] for item in requests["items"]} >= {"answered", "sent"}
