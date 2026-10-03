"""The widget config's starter questions, privacy notice and other channels."""

from tests.e2e.harness import Workshop
from tests.e2e.journeys import WIZARD_STEPS, open_restaurant
from tests.sharing.conftest import CABINET_BASE_URL


def test_starter_questions_come_from_the_faq_in_their_language(
    workshop: Workshop,
) -> None:
    restaurant = open_restaurant(workshop)

    config = workshop.client.get(f"/v1/widget/{restaurant.business_id}/config").json()

    # The published FAQ (wizard step faq_and_handoff) is in Russian.
    assert config["starter_questions"] == [{"language": "ru", "text": "Есть парковка?"}]


def test_the_footer_links_to_the_default_notice_until_the_owner_adds_one(
    workshop: Workshop,
) -> None:
    restaurant = open_restaurant(workshop)
    config_path = f"/v1/widget/{restaurant.business_id}/config"

    default = workshop.client.get(config_path).json()["privacy_url"]
    saved = workshop.client.put(
        f"{restaurant.base}/profile/steps/channels",
        json={
            "links": [
                *WIZARD_STEPS["channels"]["links"],
                {"kind": "privacy", "url": "https://salobie.example/privacy"},
            ]
        },
        headers=restaurant.headers,
    )
    own = workshop.client.get(config_path).json()["privacy_url"]

    assert default == f"{CABINET_BASE_URL}/c/{restaurant.business_id}/privacy"
    assert saved.status_code == 200, saved.text
    assert {"kind": "privacy", "url": "https://salobie.example/privacy"} in (
        workshop.client.get(
            f"{restaurant.base}/profile", headers=restaurant.headers
        ).json()["links"]
    )
    assert own == "https://salobie.example/privacy"


def test_other_channels_are_offered_with_their_links(workshop: Workshop) -> None:
    restaurant = open_restaurant(workshop)
    connected = workshop.client.put(
        f"{restaurant.base}/channels/telegram",
        json={"bot_token": "7770001:AAHbusiness_bot_token_for_sharing_tests_01"},
        headers=restaurant.headers,
    )
    assert connected.status_code == 200, connected.text

    config = workshop.client.get(f"/v1/widget/{restaurant.business_id}/config").json()

    assert config["contact_links"] == [
        {"kind": "telegram", "url": "https://t.me/workshop_bot"}
    ]
