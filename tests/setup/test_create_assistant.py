"""'Create an AI assistant': one call to a business, its setup and suggestions."""

from tests.e2e.harness import Workshop, bearer
from tests.setup.launch_steps import create_assistant, step_statuses

SETUP_ORDER: list[str] = [
    "business",
    "offer",
    "hours_and_bookings",
    "staff_contact",
    "channels",
    "test",
    "launch",
]


def test_one_call_creates_the_business_with_its_country_defaults(
    workshop: Workshop,
) -> None:
    assistant = create_assistant(workshop)

    business = assistant.created["business"]
    assert business["name"] == "Salobie Bia"
    assert business["niche_key"] == "restaurant"
    # The creator's Georgian phone decides the country and its defaults.
    assert business["country_code"] == "GE"
    assert business["timezone"] == "Asia/Tbilisi"
    assert business["currency_code"] == "GEL"
    assert business["languages"] == ["ka", "ru", "en"]
    assert business["status"] == "onboarding"
    assert business["published_assistant_version_id"] is None
    stored = workshop.client.get(assistant.base, headers=assistant.headers)
    assert stored.status_code == 200
    assert stored.json()["id"] == assistant.business_id


def test_the_new_assistant_starts_at_the_first_step_of_its_setup(
    workshop: Workshop,
) -> None:
    setup = create_assistant(workshop).created["setup"]

    assert [step["code"] for step in setup["steps"]] == SETUP_ORDER
    assert step_statuses(setup) == {
        "business": "next",
        "offer": "todo",
        "hours_and_bookings": "todo",
        "staff_contact": "todo",
        "channels": "todo",
        "test": "todo",
        "launch": "todo",
    }
    assert setup["next_step"] == "business"
    assert setup["next_action"]["target"] == "profile"
    assert setup["next_action"]["profile_step"] == "niche_and_languages"
    assert setup["percent"] == 0
    assert setup["minutes_left"] == sum(step["minutes"] for step in setup["steps"])
    assert setup["can_go_live"] is False
    assert setup["is_live"] is False
    assert setup["trial_ends_at"] is None
    assert setup["milestones"] == []
    assert setup["phone_test_links"] == []
    assert setup["apply"]["stage"] is None
    assert setup["apply"]["is_in_progress"] is False
    # Texts are in the owner's language (Georgian, from the phone).
    assert setup["language"] == "ka"
    assert setup["steps"][0]["title"] == "თქვენი ბიზნესი"


def test_the_new_assistant_comes_with_its_niche_starter_answers(
    workshop: Workshop,
) -> None:
    starters = create_assistant(workshop).created["starter_answers"]

    assert starters["niche_key"] == "restaurant"
    assert {row["state"] for row in starters["sections"]} == {"suggested"}
    # A Georgian restaurant opens every day of the week.
    assert [row["weekday"] for row in starters["hours"]] == [1, 2, 3, 4, 5, 6, 7]
    assert starters["booking_rules"]["resource_kind"] == "table"
    assert starters["resource"]["kind"] == "table"
    assert starters["handoff_rules"] != []
    assert starters["tone"]
    assert any(question["is_ready"] for question in starters["faq"])
    # Offer examples never carry a price: prices come from the owner.
    assert starters["offer_examples"] != []
    for example in starters["offer_examples"]:
        assert "price_minor" not in example


def test_the_owner_may_choose_the_country_and_languages(workshop: Workshop) -> None:
    assistant = create_assistant(
        workshop,
        {
            "name": "Studio Luce",
            "niche_key": "beauty_salon",
            "country_code": "IT",
            "languages": ["it", "en"],
            "owner_language": "en",
        },
    )

    business = assistant.created["business"]
    assert business["country_code"] == "IT"
    assert business["timezone"] == "Europe/Rome"
    assert business["currency_code"] == "EUR"
    assert business["languages"] == ["it", "en"]
    assert assistant.created["setup"]["language"] == "en"
    assert assistant.created["setup"]["steps"][0]["title"] == "Your business"
    assert assistant.created["starter_answers"]["niche_key"] == "beauty_salon"


def test_creating_needs_a_signed_in_user_and_a_valid_body(workshop: Workshop) -> None:
    anonymous = workshop.client.post(
        "/v1/assistants", json={"name": "Salobie Bia", "niche_key": "restaurant"}
    )
    assert anonymous.status_code == 401

    token, _ = workshop.sign_in_with_phone("+995 555 11 22 33")
    without_niche = workshop.client.post(
        "/v1/assistants", json={"name": "Salobie Bia"}, headers=bearer(token)
    )
    assert without_niche.status_code == 422
    unknown_niche = workshop.client.post(
        "/v1/assistants",
        json={"name": "Salobie Bia", "niche_key": "spaceport"},
        headers=bearer(token),
    )
    assert unknown_niche.status_code == 422
    listed = workshop.client.get("/v1/businesses", headers=bearer(token))
    assert listed.status_code == 200
    assert listed.json() == []
