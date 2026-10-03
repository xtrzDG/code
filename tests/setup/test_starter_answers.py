"""Accepting the niche's starter answers: empty sections only, never prices."""

from typing import Any

from tests.e2e.harness import Workshop
from tests.setup.launch_steps import (
    NewAssistant,
    create_assistant,
    invite_staff,
    read_setup,
    step_of,
)

ALL_SECTIONS: list[str] = [
    "hours",
    "booking_rules",
    "resource",
    "handoff_rules",
    "forbidden_rules",
    "tone",
    "faq",
]


def apply_starters(
    workshop: Workshop,
    assistant: NewAssistant,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    applied = workshop.client.post(
        f"{assistant.base}/setup/starter-answers/apply",
        json=body,
        headers=assistant.headers,
    )
    assert applied.status_code == 200, applied.text
    return dict(applied.json())


def starter_states(workshop: Workshop, assistant: NewAssistant) -> dict[str, str]:
    read = workshop.client.get(
        f"{assistant.base}/setup/starter-answers", headers=assistant.headers
    )
    assert read.status_code == 200, read.text
    return {row["section"]: row["state"] for row in read.json()["sections"]}


def test_accepting_fills_the_empty_profile_in_one_call(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)

    applied = apply_starters(workshop, assistant)

    assert applied["applied_sections"] == ALL_SECTIONS
    assert applied["kept_sections"] == []
    profile = applied["profile"]
    assert [day["weekday"] for day in profile["hours"]] == [1, 2, 3, 4, 5, 6, 7]
    assert profile["booking_rules"]["max_party_size"] == 8
    assert profile["booking_rules"]["deposit_minor"] is None
    assert profile["handoff_rules"] != []
    assert profile["forbidden"] != []
    assert profile["tone"]
    # Written in the owner's language (Georgian).
    assert profile["answers_language"] == "ka"
    resource = applied["resource"]
    assert resource["kind"] == "table"
    saved = applied["saved_knowledge_items"]
    assert saved != []
    assert {item["kind"] for item in saved} == {"faq"}
    assert all(item["price_minor"] is None for item in saved)
    assert set(starter_states(workshop, assistant).values()) == {"already_set"}


def test_suggestions_never_count_as_prices(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    apply_starters(workshop, assistant)

    setup = read_setup(workshop, assistant)

    hours = step_of(setup, "hours_and_bookings")
    offer = step_of(setup, "offer")
    assert hours["status"] == "done"
    assert hours["missing"] == []
    assert offer["status"] != "done"
    assert offer["missing"] == ["no_priced_items"]
    items = workshop.client.get(
        f"{assistant.base}/knowledge", headers=assistant.headers
    ).json()["items"]
    assert items != []
    assert all(row["price_minor"] is None for row in items)


def test_accepting_again_changes_nothing(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    first = apply_starters(workshop, assistant)

    again = apply_starters(workshop, assistant)

    assert again["applied_sections"] == []
    assert again["kept_sections"] == ALL_SECTIONS
    assert again["saved_knowledge_items"] == []
    assert again["resource"] is None
    assert again["profile"] == first["profile"]
    audit = workshop.client.get(
        f"{assistant.base}/audit-log",
        params={"entity": "business_profile.starter_answers"},
        headers=assistant.headers,
    ).json()["items"]
    assert len(audit) == 1
    assert audit[0]["actor_id"] == assistant.owner_id


def test_a_section_the_owner_filled_is_kept(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    own_tone = workshop.client.patch(
        f"{assistant.base}/profile",
        json={"tone": "Коротко и по делу"},
        headers=assistant.headers,
    )
    assert own_tone.status_code == 200, own_tone.text
    assert starter_states(workshop, assistant)["tone"] == "already_set"

    applied = apply_starters(workshop, assistant, {"sections": ["tone", "hours"]})

    assert applied["applied_sections"] == ["hours"]
    assert applied["kept_sections"] == ["tone"]
    profile = applied["profile"]
    assert profile["tone"] == "Коротко и по делу"
    assert profile["handoff_rules"] == []
    assert applied["saved_knowledge_items"] == []


def test_the_owner_may_take_some_questions_in_another_language(
    workshop: Workshop,
) -> None:
    assistant = create_assistant(workshop)

    applied = apply_starters(
        workshop,
        assistant,
        {"sections": ["faq"], "faq_keys": ["book_table"], "language": "ru"},
    )

    assert applied["applied_sections"] == ["faq"]
    saved = applied["saved_knowledge_items"]
    assert [item["title"] for item in saved] == ["Как забронировать стол?"]


def test_sections_a_niche_does_not_suggest_are_refused(workshop: Workshop) -> None:
    shop = create_assistant(
        workshop, {"name": "Tbilisi Tea", "niche_key": "online_shop"}
    )
    offered = starter_states(workshop, shop)
    assert "resource" not in offered
    assert "booking_rules" not in offered

    refused = workshop.client.post(
        f"{shop.base}/setup/starter-answers/apply",
        json={"sections": ["resource"]},
        headers=shop.headers,
    )

    assert refused.status_code == 422, refused.text
    resources = workshop.client.get(f"{shop.base}/resources", headers=shop.headers)
    assert resources.json() == {"items": []}


def test_staff_read_the_suggestions_but_only_owners_accept_them(
    workshop: Workshop,
) -> None:
    assistant = create_assistant(workshop)
    staff = invite_staff(workshop, assistant)

    read = workshop.client.get(
        f"{assistant.base}/setup/starter-answers",
        params={"language": "en"},
        headers=staff,
    )
    refused = workshop.client.post(
        f"{assistant.base}/setup/starter-answers/apply", headers=staff
    )

    assert read.status_code == 200
    assert read.json()["language"] == "en"
    assert read.json()["faq"][0]["question"] == "How can I book a table?"
    assert refused.status_code == 403
    assert set(starter_states(workshop, assistant).values()) == {"suggested"}
