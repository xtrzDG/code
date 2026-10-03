"""Autosave of the profile: PATCH changes only the fields sent, on every edit."""

from typing import Any

from tests.e2e.harness import Workshop
from tests.setup.launch_steps import NewAssistant, create_assistant, invite_staff

MONDAY_NINE_TO_SIX: list[dict[str, int]] = [
    {"weekday": 1, "opens_at": 540, "closes_at": 1080}
]


def patch_profile(
    workshop: Workshop,
    assistant: NewAssistant,
    body: dict[str, Any],
    expected_status: int = 200,
) -> dict[str, Any]:
    patched = workshop.client.patch(
        f"{assistant.base}/profile", json=body, headers=assistant.headers
    )
    assert patched.status_code == expected_status, patched.text
    return dict(patched.json())


def contact_audit_count(workshop: Workshop, assistant: NewAssistant) -> int:
    entries = workshop.client.get(
        f"{assistant.base}/audit-log",
        params={"entity": "business_profile.contacts"},
        headers=assistant.headers,
    ).json()["items"]
    return len(entries)


def test_each_field_is_saved_on_its_own(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)

    patch_profile(workshop, assistant, {"tone": "Тепло и коротко"})
    saved = patch_profile(workshop, assistant, {"hours": MONDAY_NINE_TO_SIX})

    assert saved["tone"] == "Тепло и коротко"
    assert saved["hours"] == MONDAY_NINE_TO_SIX
    assert saved["is_saved"] is True
    read = workshop.client.get(f"{assistant.base}/profile", headers=assistant.headers)
    assert read.json()["tone"] == "Тепло и коротко"
    assert read.json()["hours"] == MONDAY_NINE_TO_SIX


def test_an_explicit_null_clears_a_section_and_absence_keeps_it(
    workshop: Workshop,
) -> None:
    assistant = create_assistant(workshop)
    patch_profile(workshop, assistant, {"tone": "Тепло", "hours": MONDAY_NINE_TO_SIX})

    cleared = patch_profile(workshop, assistant, {"tone": None})

    assert cleared["tone"] is None
    assert cleared["hours"] == MONDAY_NINE_TO_SIX


def test_answers_and_contact_phones_change_one_at_a_time(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)

    patch_profile(
        workshop,
        assistant,
        {"answers": [{"question_key": "cuisine", "answer": "Грузинская"}]},
    )
    patch_profile(
        workshop, assistant, {"contacts": {"public_phone_number": "+995 322 12 34 56"}}
    )
    saved = patch_profile(
        workshop, assistant, {"contacts": {"handoff_phone_number": "555 98 76 54"}}
    )

    assert saved["niche_answers"] == [
        {"question_key": "cuisine", "answer": "Грузинская"}
    ]
    # Phones are parsed in the business's country and stored in E.164.
    assert saved["contacts"] == {
        "public_phone_number": "+995322123456",
        "handoff_phone_number": "+995555987654",
    }
    assert contact_audit_count(workshop, assistant) == 2


def test_a_patch_that_changes_nothing_keeps_the_revision(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    first = patch_profile(workshop, assistant, {"tone": "Тепло"})

    same = patch_profile(workshop, assistant, {"tone": "Тепло"})
    empty = patch_profile(workshop, assistant, {})

    assert same["updated_at"] == first["updated_at"]
    assert empty["updated_at"] == first["updated_at"]
    assert contact_audit_count(workshop, assistant) == 0


def test_an_edit_from_an_older_profile_is_refused(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    seen = patch_profile(workshop, assistant, {"tone": "Тепло"})
    newer = patch_profile(workshop, assistant, {"hours": MONDAY_NINE_TO_SIX})

    refused = patch_profile(
        workshop,
        assistant,
        {"expected_updated_at": seen["updated_at"], "tone": "Строго"},
        expected_status=409,
    )
    accepted = patch_profile(
        workshop,
        assistant,
        {"expected_updated_at": newer["updated_at"], "tone": "Строго"},
    )

    assert refused["error"] == "conflict"
    assert refused["reasons"][0]["code"] == "stale_revision"
    assert refused["reasons"][0]["details"] == [str(newer["updated_at"])]
    assert accepted["tone"] == "Строго"
    assert int(accepted["updated_at"]) > int(newer["updated_at"])


def test_a_rejected_field_changes_nothing(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    before = patch_profile(workshop, assistant, {"tone": "Тепло"})

    backwards = patch_profile(
        workshop,
        assistant,
        {
            "tone": "Строго",
            "hours": [{"weekday": 1, "opens_at": 1080, "closes_at": 540}],
        },
        expected_status=422,
    )
    unknown_question = patch_profile(
        workshop,
        assistant,
        {"answers": [{"question_key": "warp_drive", "answer": "yes"}]},
        expected_status=422,
    )
    unknown_field = patch_profile(
        workshop, assistant, {"colour": "teal"}, expected_status=422
    )

    assert "closes before it opens" in backwards["message"]
    assert "warp_drive" in unknown_question["message"]
    assert "colour" in unknown_field["message"]
    read = workshop.client.get(f"{assistant.base}/profile", headers=assistant.headers)
    assert read.json()["tone"] == "Тепло"
    assert read.json()["updated_at"] == before["updated_at"]


def test_only_owners_autosave(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    staff = invite_staff(workshop, assistant)

    refused = workshop.client.patch(
        f"{assistant.base}/profile", json={"tone": "Тепло"}, headers=staff
    )

    assert refused.status_code == 403
